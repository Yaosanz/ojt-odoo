from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OjtProgress(models.Model):
    _name = "ojt.progress"
    _description = "OJT Progress Tracking"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'week desc'

    participant_id = fields.Many2one('ojt.participant', string="Participant", required=True,
                                     ondelete='cascade', tracking=True)
    batch_id = fields.Many2one('ojt.batch', string="Batch", related='participant_id.batch_id', store=True)
    week = fields.Integer(string="Week Number", tracking=True)
    description = fields.Text(string="Activity / Task Description", tracking=True)
    evaluation = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
    ], string="Evaluation", default='good', tracking=True)
    mentor_notes = fields.Text(string="Mentor Notes", tracking=True)
    date_recorded = fields.Date(string="Date Recorded", default=fields.Date.today, tracking=True)
    progress_percentage = fields.Float(string="Progress Percentage", default=0.0, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)

    @api.constrains('week')
    def _check_week(self):
        for record in self:
            if record.week and record.week <= 0:
                raise ValidationError(_('Week number must be positive.'))
