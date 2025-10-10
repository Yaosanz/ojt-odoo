from odoo import models, fields

class OjtProgress(models.Model):
    _name = "ojt.progress"
    _description = "OJT Progress Tracking"

    participant_id = fields.Many2one('ojt.participant', string="Participant", required=True, ondelete='cascade')
    batch_id = fields.Many2one('ojt.batch', string="Batch", related='participant_id.batch_id', store=True)
    week = fields.Integer(string="Week Number")
    description = fields.Text(string="Activity / Task Description")
    evaluation = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
    ], string="Evaluation", default='good')
    mentor_notes = fields.Text(string="Mentor Notes")
