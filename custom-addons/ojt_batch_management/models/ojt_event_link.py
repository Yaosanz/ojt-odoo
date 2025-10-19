from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OjtEventLink(models.Model):
    _name = "ojt.event.link"
    _description = "OJT Event / Agenda"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'event_date desc'

    name = fields.Char(string="Event Title", required=True, tracking=True)
    event_date = fields.Date(string="Date", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    supervisor = fields.Char(string="Supervisor / Mentor", tracking=True)
    batch_id = fields.Many2one('ojt.batch', string="Batch", ondelete='cascade', tracking=True)
    event_id = fields.Many2one('event.event', string="Related Event", tracking=True)
    is_mandatory = fields.Boolean(string="Mandatory Attendance", default=True, tracking=True)
    weight = fields.Float(string="Weight (%)", default=1.0, tracking=True)
    online_meeting_url = fields.Char(string="Online Meeting URL", tracking=True)
    notes = fields.Text(string="Additional Notes", tracking=True)
    status = fields.Selection([
        ('planned', 'Planned'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done'),
    ], string="Status", default='planned', tracking=True)
    meeting_attendance_ids = fields.One2many('ojt.meeting.attendance', 'event_link_id', string='Meeting Attendances')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)

    @api.constrains('weight')
    def _check_weight(self):
        for record in self:
            if record.weight <= 0 or record.weight > 100:
                raise ValidationError(_('Weight must be between 0.01 and 100.'))

    @api.constrains('event_date')
    def _check_event_date(self):
        for record in self:
            if record.batch_id and record.event_date:
                if record.event_date < record.batch_id.start_date or record.event_date > record.batch_id.end_date:
                    raise ValidationError(_('Event date must be within batch period.'))

    @api.model
    def create(self, vals):
        return super().create(vals)

    def action_mark_done(self):
        self.write({'status': 'done'})

    def action_start_event(self):
        self.write({'status': 'ongoing'})

    def action_auto_close_attendance(self):
        """Cron job to auto-close attendance for past events"""
        past_events = self.search([
            ('event_date', '<', fields.Date.today()),
            ('status', '!=', 'done')
        ])
        past_events.write({'status': 'done'})
