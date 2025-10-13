import uuid
from odoo import models, fields, api, _

from odoo.exceptions import ValidationError


class OjtParticipant(models.Model):
    _name = 'ojt.participant'
    _description = 'OJT Participant'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(compute='_compute_name', store=True, string='Participant Name', tracking=True)
    batch_id = fields.Many2one('ojt.batch', string='Batch', required=True, ondelete='cascade', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, tracking=True)
    applicant_id = fields.Many2one('hr.applicant', string='From Application', tracking=True)
    registration_id = fields.Many2one('event.registration', string='Event Registration', tracking=True)

    # course_ids = fields.Many2many('slide.channel', 'ojt_participant_channel_rel',
    #                               string='Enrolled Courses', tracking=True)

    attendance_count = fields.Integer(compute='_compute_kpi', store=True, string='Total Attendances')
    attendance_rate = fields.Float(compute='_compute_kpi', store=True, string='Attendance Rate %')
    assignment_submit_ids = fields.One2many('ojt.assignment.submit', 'participant_id', string='Submissions')
    score_avg = fields.Float(compute='_compute_kpi', store=True, string='Average Score')
    score_final = fields.Float(compute='_compute_kpi', store=True, string='Final Score')
    mentor_score = fields.Float(string='Mentor Score', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('left', 'Left'),
    ], string='Status', default='active', tracking=True, track_visibility='onchange')

    certificate_id = fields.Many2one('ojt.certificate', string='Certificate', readonly=True)
    portal_token = fields.Char(string='Portal Token', index=True, readonly=True)
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)

    # Related fields for convenience
    student_id = fields.Char(related='partner_id.ref', string='Student ID', store=True)
    email = fields.Char(related='partner_id.email', string='Email', store=True)
    phone = fields.Char(related='partner_id.phone', string='Phone', store=True)
    department = fields.Char(related='batch_id.department_id.name', string='Department', store=True)
    company_name = fields.Char(related='partner_id.parent_name', string='Company', store=True)
    start_date = fields.Date(related='batch_id.start_date', string='Start Date', store=True)
    end_date = fields.Date(related='batch_id.end_date', string='End Date', store=True)
    user_id = fields.Many2one('res.users', string='Portal User', readonly=True,
                              related='partner_id.user_id', store=True)

    @api.depends('partner_id.name', 'batch_id.name')
    def _compute_name(self):
        for record in self:
            if record.partner_id and record.batch_id:
                record.name = f"{record.partner_id.name} - {record.batch_id.name}"
            elif record.partner_id:
                record.name = record.partner_id.name
            else:
                record.name = "New Participant"

    @api.depends('batch_id.event_link_ids', 'batch_id.event_link_ids.is_mandatory')
    def _compute_kpi(self):
        for record in self:
            # Attendance calculation
            attendances = self.env['ojt.attendance'].search([
                ('participant_id', '=', record.id),
                ('presence', 'in', ('present', 'late'))
            ])
            mandatory_events = record.batch_id.event_link_ids.filtered(lambda e: e.is_mandatory)
            record.attendance_count = len(attendances)
            record.attendance_rate = (len(attendances) / len(mandatory_events) * 100) if mandatory_events else 0.0

            # Score calculation
            submissions = record.assignment_submit_ids.filtered(lambda s: s.state in ('submitted', 'scored'))
            if submissions:
                scores = []
                for sub in submissions:
                    if sub.assignment_id.max_score:
                        normalized_score = (sub.score / sub.assignment_id.max_score) * 100 * sub.assignment_id.weight
                        scores.append(normalized_score)
                record.score_avg = sum(scores) / len(scores) if scores else 0.0
                # Final score includes mentor score if available
                mentor_weight = 0.2  # 20% weight for mentor score
                assignment_weight = 0.8  # 80% weight for assignments
                record.score_final = (record.score_avg * assignment_weight) + (record.mentor_score * mentor_weight) if record.mentor_score else record.score_avg
            else:
                record.score_avg = 0.0
                record.score_final = record.mentor_score or 0.0

    @api.model
    def create(self, vals):
        if 'portal_token' not in vals:
            vals['portal_token'] = str(uuid.uuid4())
        record = super().create(vals)
        # Auto-create portal user if email exists
        if record.partner_id.email and not record.user_id:
            user = self.env['res.users'].sudo().create({
                'name': record.partner_id.name,
                'login': record.partner_id.email,
                'email': record.partner_id.email,
                'partner_id': record.partner_id.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
        return record

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_fail(self):
        self.write({'state': 'failed'})

    def action_left(self):
        self.write({'state': 'left'})
