from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OjtAssignment(models.Model):
    _name = 'ojt.assignment'
    _description = 'OJT Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'deadline desc'

    name = fields.Char(string='Assignment Title', required=True, tracking=True)
    batch_id = fields.Many2one('ojt.batch', string='Batch', required=True, ondelete='cascade', tracking=True)
    event_link_id = fields.Many2one('ojt.event.link', string='Related Event', ondelete='set null',
                                    domain="[('batch_id', '=', batch_id)]")
    description = fields.Html(string='Description')
    type = fields.Selection([
        ('task', 'Task/Project'),
        ('quiz', 'Quiz (Survey/Slides)'),
        ('presentation', 'Presentation'),
    ], string='Type', default='task', required=True, tracking=True)
    # related_channel_id = fields.Many2one('slide.channel', string='Related Course',
    #                                      domain="[('id', 'in', batch_id.course_ids.ids)]")
    deadline = fields.Datetime(string='Deadline', required=True, tracking=True)
    max_score = fields.Float(string='Max Score', default=100.0, required=True)
    weight = fields.Float(string='Weight', default=1.0, required=True,
                          help='Weight for final score calculation')
    attachment_required = fields.Boolean(string='Attachment Required', default=True)
    submit_ids = fields.One2many('ojt.assignment.submit', 'assignment_id', string='Submissions')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='State', default='open', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)

    # Computed fields
    submission_count = fields.Integer(compute='_compute_submission_stats', store=True)
    average_score = fields.Float(compute='_compute_submission_stats', store=True)
    completion_rate = fields.Float(compute='_compute_submission_stats', store=True)

    # Alias field for backward compatibility
    submit_count = fields.Integer(related='submission_count', string="Submission Count", store=True)

    @api.depends('submit_ids.score', 'submit_ids.state', 'batch_id.participant_ids')
    def _compute_submission_stats(self):
        for record in self:
            submissions = record.submit_ids.filtered(lambda s: s.state in ('submitted', 'scored'))
            record.submission_count = len(submissions)
            if submissions:
                scored_subs = submissions.filtered(lambda s: s.score is not False)
                record.average_score = sum(scored_subs.mapped('score')) / len(scored_subs) if scored_subs else 0.0
                record.completion_rate = (len(submissions) / len(record.batch_id.participant_ids)) * 100 if record.batch_id.participant_ids else 0.0
            else:
                record.average_score = 0.0
                record.completion_rate = 0.0

    @api.constrains('max_score', 'weight')
    def _check_constraints(self):
        for record in self:
            if record.max_score <= 0:
                raise ValidationError(_('Max score must be greater than 0.'))
            if record.weight <= 0:
                raise ValidationError(_('Weight must be greater than 0.'))

    @api.constrains('deadline')
    def _check_deadline(self):
        for record in self:
            if record.deadline and record.deadline < fields.Datetime.now():
                raise ValidationError(_('Deadline cannot be in the past.'))

    def action_open(self):
        self.write({'state': 'open'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_auto_close_overdue(self):
        """Cron job to close assignments past deadline"""
        overdue = self.search([
            ('deadline', '<', fields.Datetime.now()),
            ('state', '=', 'open')
        ])
        overdue.action_close()

    def action_send_reminders(self):
        """Cron job to send assignment reminders"""
        # Implementation for sending reminders
        pass
