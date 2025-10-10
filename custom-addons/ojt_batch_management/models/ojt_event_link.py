from odoo import models, fields

class OjtEventLink(models.Model):
    _name = "ojt.event.link"
    _description = "OJT Event / Agenda"

    name = fields.Char(string="Event Title", required=True)
    event_date = fields.Date(string="Date", required=True)
    description = fields.Text(string="Description")
    supervisor = fields.Char(string="Supervisor / Mentor")
    batch_id = fields.Many2one('ojt.batch', string="Batch", ondelete='cascade')
    status = fields.Selection([
        ('planned', 'Planned'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done'),
    ], string="Status", default='planned')
