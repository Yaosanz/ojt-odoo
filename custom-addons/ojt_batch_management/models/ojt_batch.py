import uuid
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OjtBatch(models.Model):
    _name = "ojt.batch"
    _description = "OJT Batch"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    name = fields.Char(string="Batch Name", required=True, tracking=True)
    code = fields.Char(string="Batch Code", required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), tracking=True)
    job_id = fields.Many2one('hr.job', string='Related Job Position', tracking=True)
    description = fields.Html(string='Description')
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    mentor_ids = fields.Many2many('res.partner', 'ojt_batch_mentor_rel',
                                  string='Mentors/Instructors', tracking=True)

    start_date = fields.Date(string="Start Date", required=True, tracking=True)
    end_date = fields.Date(string="End Date", required=True, tracking=True)
    mode = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('hybrid', 'Hybrid'),
    ], string="Mode", default='online', required=True, tracking=True)
    capacity = fields.Integer(string='Capacity', tracking=True)

    participant_ids = fields.One2many('ojt.participant', 'batch_id', string='Participants')
    event_link_ids = fields.One2many('ojt.event.link', 'batch_id', string='Event Links')
    survey_id = fields.Many2one('survey.survey', string='Evaluation Survey', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('recruit', 'Recruitment'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string="Status", default='draft', tracking=True, track_visibility='onchange')

    certificate_rule_attendance = fields.Float(string='Min Attendance %', default=80.0,
                                               help='Minimum attendance percentage for certificate')
    certificate_rule_score = fields.Float(string='Min Final Score', default=70.0,
                                          help='Minimum final score for certificate')

    progress_ratio = fields.Float(compute='_compute_progress_ratio', store=True,
                                  string='Progress %')
    color = fields.Integer(string='Color', default=0)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    # Computed fields
    participant_count = fields.Integer(compute='_compute_counts', store=True)
    assignment_count = fields.Integer(compute='_compute_counts', store=True)
    event_count = fields.Integer(compute='_compute_counts', store=True)

    def _compute_counts(self):
        for record in self:
            record.participant_count = len(record.participant_ids)
            assignments = self.env['ojt.assignment'].search([('batch_id', '=', record.id)])
            record.assignment_count = len(assignments)
            record.event_count = len(record.event_link_ids)

    def _compute_progress_ratio(self):
        for record in self:
            if not record.participant_ids:
                record.progress_ratio = 0.0
                continue
            completed = len(record.participant_ids.filtered(lambda p: p.state == 'completed'))
            record.progress_ratio = (completed / len(record.participant_ids)) * 100

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_('End date must be after start date.'))

    @api.constrains('certificate_rule_attendance', 'certificate_rule_score')
    def _check_rules(self):
        for record in self:
            if not (0 <= record.certificate_rule_attendance <= 100):
                raise ValidationError(_('Attendance rule must be between 0 and 100.'))
            if record.certificate_rule_score < 0:
                raise ValidationError(_('Score rule must be non-negative.'))

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('ojt.batch') or _('New')
        return super().create(vals)

    def action_recruit(self):
        self.write({'state': 'recruit'})

    def action_start(self):
        self.write({'state': 'ongoing'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_generate_certificates(self):
        """Wizard action to generate certificates for eligible participants"""
        eligible = self.participant_ids.filtered(
            lambda p: p.attendance_rate >= self.certificate_rule_attendance
            and p.score_final >= self.certificate_rule_score
            and p.state == 'completed'
        )
        certificates = []
        for participant in eligible:
            cert_vals = {
                'participant_id': participant.id,
                'qr_token': str(uuid.uuid4()),
                'state': 'issued',
            }
            certificates.append(self.env['ojt.certificate'].create(cert_vals))
        return certificates

    def action_auto_state_transition(self):
        """Cron job to auto-transition batch states based on dates"""
        today = fields.Date.today()
        # Draft to recruit if start date is approaching
        draft_batches = self.search([
            ('state', '=', 'draft'),
            ('start_date', '<=', today)
        ])
        draft_batches.action_recruit()

        # Ongoing to done if end date has passed
        ongoing_batches = self.search([
            ('state', '=', 'ongoing'),
            ('end_date', '<', today)
        ])
        ongoing_batches.action_done()
