from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OjtAttendance(models.Model):
    _name = "ojt.attendance"
    _description = "OJT Attendance Record"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "check_in desc"

    batch_id = fields.Many2one('ojt.batch', string="Batch", related='participant_id.batch_id', store=True, readonly=True, tracking=True)
    event_link_id = fields.Many2one('ojt.event.link', string="Event", required=True,
                                    domain="[('batch_id', '=', batch_id)]", tracking=True)
    event_id = fields.Many2one('event.event', string="Event", related='event_link_id.event_id', store=True)
    participant_id = fields.Many2one('ojt.participant', string="Participant", required=True,
                                     domain="[('batch_id', '=', batch_id)]", tracking=True)

    check_in = fields.Datetime(string="Check In", tracking=True)
    check_out = fields.Datetime(string="Check Out", tracking=True)
    presence = fields.Selection([
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
    ], string="Presence", default='present', required=True, tracking=True)
    method = fields.Selection([
        ('qr', 'QR Scan'),
        ('online', 'Online Join'),
        ('manual', 'Manual'),
    ], string="Check Method", default='manual', required=True, tracking=True)
    duration_minutes = fields.Float(compute='_compute_duration', store=True, string='Duration (min)')
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_attendance', 'unique(participant_id, event_link_id)',
         'Participant attendance already recorded for this event!')
    ]

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for record in self:
            if record.check_in and record.check_out:
                duration = (record.check_out - record.check_in).total_seconds() / 60
                record.duration_minutes = max(0, duration)
            else:
                record.duration_minutes = 0.0

    @api.constrains('check_in', 'check_out')
    def _check_times(self):
        for record in self:
            if record.check_in and record.check_out and record.check_in > record.check_out:
                raise ValidationError(_('Check out time must be after check in time.'))

    @api.constrains('presence')
    def _check_presence_logic(self):
        for record in self:
            if record.presence == 'present' and not record.check_in:
                raise ValidationError(_('Check in time is required for present status.'))

    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Auto-set presence based on check-in time vs event start
        if record.check_in and record.event_link_id and record.event_link_id.event_id:
            event_start = record.event_link_id.event_id.date_begin
            if event_start and record.check_in > event_start:
                # If check-in is more than 15 minutes late, mark as late
                if (record.check_in - event_start).total_seconds() / 60 > 15:
                    record.presence = 'late'
        return record

    def action_mark_present(self):
        self.write({'presence': 'present'})

    def action_mark_late(self):
        self.write({'presence': 'late'})

    def action_mark_absent(self):
        self.write({'presence': 'absent'})
