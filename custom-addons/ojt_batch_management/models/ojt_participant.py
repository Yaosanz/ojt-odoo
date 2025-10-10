from odoo import models, fields, api

class OjtParticipant(models.Model):
    _name = 'ojt.participant'
    _description = 'OJT Participant'

    name = fields.Char(string='Participant Name', required=True)
    student_id = fields.Char(string='Student ID', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    department = fields.Char(string='Department')
    batch_id = fields.Many2one('ojt.batch', string='Batch', required=True, ondelete='cascade')
    company_name = fields.Char(string='Company')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    status = fields.Selection([
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped')
    ], string='Status', default='ongoing')
    user_id = fields.Many2one('res.users', string='Portal User', readonly=True)

    @api.model
    def create(self, vals):
        record = super(OjtParticipant, self).create(vals)
        if record.email and not record.user_id:
            # Buat user portal otomatis
            user = self.env['res.users'].sudo().create({
                'name': record.name,
                'login': record.email,
                'email': record.email,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
            record.user_id = user.id
        return record
