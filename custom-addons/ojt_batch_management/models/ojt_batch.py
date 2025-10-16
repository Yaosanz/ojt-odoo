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
    ojt_batch_ids = fields.One2many('hr.applicant', 'ojt_batch_id', string='Applications')
    description = fields.Html(string='Description')
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    employee_id = fields.Char(string='ID Pegawai')
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
    qr_token = fields.Char(string='QR Token', unique=True, index=True)

    _sql_constraints = [
        ('unique_qr_token', 'unique(qr_token)', 'QR Token must be unique!'),
    ]

    # Computed fields
    participant_count = fields.Integer(compute='_compute_counts', store=True)
    assignment_count = fields.Integer(compute='_compute_counts', store=True)
    event_count = fields.Integer(compute='_compute_counts', store=True)
    
    # Smart button counters
    scheduled_count = fields.Integer(compute='_compute_state_counts', store=True)
    ongoing_count = fields.Integer(compute='_compute_state_counts', store=True)
    completed_count = fields.Integer(compute='_compute_state_counts', store=True)
    cancelled_count = fields.Integer(compute='_compute_state_counts', store=True)

    def _compute_counts(self):
        for record in self:
            record.participant_count = len(record.participant_ids)
            assignments = self.env['ojt.assignment'].search([('batch_id', '=', record.id)])
            record.assignment_count = len(assignments)
            record.event_count = len(record.event_link_ids)
            
    @api.depends('participant_ids.state')
    def _compute_state_counts(self):
        for record in self:
            participants = record.participant_ids
            record.scheduled_count = len(participants.filtered(lambda p: p.state == 'draft'))
            record.ongoing_count = len(participants.filtered(lambda p: p.state == 'ongoing'))
            record.completed_count = len(participants.filtered(lambda p: p.state == 'completed'))
            record.cancelled_count = len(participants.filtered(lambda p: p.state in ['failed', 'left']))

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
        """Generate certificates for eligible participants"""
        eligible = self.participant_ids.filtered(
            lambda p: p.attendance_rate >= self.certificate_rule_attendance
            and p.score_final >= self.certificate_rule_score
            and p.state == 'completed'
        )

        if not eligible:
            raise ValidationError(_('No eligible participants found for certificate generation.'))

        certificates = []
        for participant in eligible:
            # Check if certificate already exists
            existing_cert = self.env['ojt.certificate'].search([
                ('participant_id', '=', participant.id)
            ], limit=1)

            if existing_cert:
                continue  # Skip if certificate already exists

            # Create certificate
            cert_vals = {
                'participant_id': participant.id,
                'qr_token': str(uuid.uuid4()),
                'state': 'draft',  # Start as draft, then issue
            }
            certificate = self.env['ojt.certificate'].create(cert_vals)

            # Issue the certificate (generate PDF and send email)
            try:
                certificate.action_issue()
                certificates.append(certificate)
            except Exception as e:
                # Log error but continue with other certificates
                self.env['ir.logging'].sudo().create({
                    'name': 'ojt_batch_management',
                    'type': 'server',
                    'dbname': self.env.cr.dbname,
                    'level': 'ERROR',
                    'message': f'Failed to generate certificate for participant {participant.name}: {str(e)}',
                    'path': 'ojt_batch.action_generate_certificates',
                    'line': '0',
                    'func': 'action_generate_certificates',
                })

        if certificates:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Certificates Generated'),
                    'message': _('Successfully generated %d certificates.') % len(certificates),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Certificates Generated'),
                    'message': _('All eligible participants already have certificates or generation failed.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

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

    def action_view_scheduled(self):
        """Smart button action to view scheduled participants"""
        return {
            'name': 'Scheduled Participants',
            'type': 'ir.actions.act_window',
            'res_model': 'ojt.participant',
            'view_mode': 'kanban,list,form',
            'domain': [('batch_id', '=', self.id), ('state', '=', 'draft')],
            'context': {'default_batch_id': self.id}
        }

    def action_view_ongoing(self):
        """Smart button action to view ongoing participants"""
        return {
            'name': 'Ongoing Participants',
            'type': 'ir.actions.act_window',
            'res_model': 'ojt.participant',
            'view_mode': 'kanban,list,form',
            'domain': [('batch_id', '=', self.id), ('state', '=', 'ongoing')],
            'context': {'default_batch_id': self.id}
        }

    def action_view_completed(self):
        """Smart button action to view completed participants"""
        return {
            'name': 'Completed Participants',
            'type': 'ir.actions.act_window',
            'res_model': 'ojt.participant',
            'view_mode': 'kanban,list,form',
            'domain': [('batch_id', '=', self.id), ('state', '=', 'completed')],
            'context': {'default_batch_id': self.id}
        }

    def action_view_cancelled(self):
        """Smart button action to view cancelled participants"""
        return {
            'name': 'Cancelled Participants',
            'type': 'ir.actions.act_window',
            'res_model': 'ojt.participant',
            'view_mode': 'kanban,list,form',
            'domain': [('batch_id', '=', self.id), ('state', 'in', ['failed', 'left'])],
            'context': {'default_batch_id': self.id}
        }
