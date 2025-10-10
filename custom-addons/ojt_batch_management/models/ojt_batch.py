from odoo import models, fields

class OjtBatch(models.Model):
    _name = "ojt.batch"
    _description = "OJT Batch"

    name = fields.Char(string="Batch Name", required=True)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('done', 'Done'),
    ], string="Status", default='draft')
