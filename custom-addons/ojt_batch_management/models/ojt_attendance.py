from odoo import models, fields, api

class OjtAttendance(models.Model):
    _name = "ojt.attendance"
    _description = "OJT Attendance Record"
    _order = "date desc"

    participant_id = fields.Many2one('ojt.participant', string="Participant", required=True, ondelete='cascade')
    batch_id = fields.Many2one('ojt.batch', string="Batch", related='participant_id.batch_id', store=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ], string="Status", default='present', required=True)
    remarks = fields.Char(string="Remarks")

    _sql_constraints = [
        ('unique_attendance', 'unique(participant_id, date)',
         'Participant attendance already recorded for this date!')
    ]
