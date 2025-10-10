from odoo import models, fields

class CollegeTeacher(models.Model):
    _name = 'college.teacher'
    _description = 'Data Dosen'

    name = fields.Char(string='Nama Dosen', required=True)
    employee_id = fields.Char(string='ID Pegawai')
    department = fields.Char(string='Jurusan')
    phone = fields.Char(string='No. Telepon')
    students = fields.One2many('college.student', 'teacher_id', string='Mahasiswa Bimbingan')
