from odoo import models, fields

class CollegeStudent(models.Model):
    _name = 'college.student'
    _description = 'Data Mahasiswa'

    name = fields.Char(string='Nama Mahasiswa', required=True)
    student_id = fields.Char(string='NIM', required=True)
    age = fields.Integer(string='Usia')
    gender = fields.Selection([
        ('male', 'Laki-laki'),
        ('female', 'Perempuan'),
    ], string='Jenis Kelamin')
    teacher_id = fields.Many2one('college.teacher', string='Dosen Pembimbing')
    active = fields.Boolean(default=True)
