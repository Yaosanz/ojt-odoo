from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OjtAssignmentSubmit(models.Model):
    _name = 'ojt.assignment.submit'
    _description = 'OJT Assignment Submission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submitted_on desc'

    assignment_id = fields.Many2one('ojt.assignment', string='Assignment', required=True,
                                    ondelete='cascade', tracking=True)
    participant_id = fields.Many2one('ojt.participant', string='Participant', required=True,
                                     ondelete='cascade', tracking=True)
    batch_id = fields.Many2one('ojt.batch', related='assignment_id.batch_id', store=True)

    submitted_on = fields.Datetime(string='Submitted On', default=fields.Datetime.now, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', 'ojt_assignment_submit_attachment_rel',
                                      string='Attachments')
    url_link = fields.Char(string='URL/Link')
    score = fields.Float(string='Score')
    reviewer_id = fields.Many2one('res.users', string='Reviewer', tracking=True)
    feedback = fields.Html(string='Feedback')
    late = fields.Boolean(string='Late Submission', compute='_compute_late', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('scored', 'Scored'),
    ], string='State', default='submitted', tracking=True)

    _sql_constraints = [
        ('unique_submission', 'unique(assignment_id, participant_id)',
         'Each participant can only submit once per assignment!')
    ]

    @api.depends('submitted_on', 'assignment_id.deadline')
    def _compute_late(self):
        for record in self:
            record.late = record.submitted_on > record.assignment_id.deadline if record.submitted_on and record.assignment_id.deadline else False

    @api.constrains('score')
    def _check_score(self):
        for record in self:
            if record.score and record.score > record.assignment_id.max_score:
                raise ValidationError(_('Score cannot exceed maximum score of %s') % record.assignment_id.max_score)

    @api.constrains('attachment_ids', 'url_link')
    def _check_attachments(self):
        for record in self:
            if record.assignment_id.attachment_required and not record.attachment_ids and not record.url_link:
                raise ValidationError(_('At least one attachment or URL is required for this assignment.'))

    def action_submit(self):
        """Action to submit the assignment"""
        for record in self:
            record.state = 'submitted'

    def action_score(self):
        """Action to mark submission as scored"""
        self.ensure_one()
        if not self.score:
            raise ValidationError(_('Please enter a score before marking as scored.'))
        self.write({
            'state': 'scored',
            'reviewer_id': self.env.user.id,
        })

    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Auto-set late flag
        record._compute_late()
        return record

    def write(self, vals):
        res = super().write(vals)
        if 'score' in vals and vals.get('score'):
            self.filtered(lambda r: r.state == 'submitted').write({'state': 'scored'})
        return res
