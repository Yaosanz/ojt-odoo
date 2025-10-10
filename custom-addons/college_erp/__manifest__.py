{
    'name': 'College ERP',
    'version': '1.0',
    'summary': 'Sistem ERP sederhana untuk manajemen kampus',
    'sequence': 10,
    'description': """
Manajemen kampus: Mahasiswa, Dosen, dan data akademik sederhana.
""",
    'author': 'Sandy',
    'website': 'https://example.com',
    'category': 'Education',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/student_views.xml',
        'views/teacher_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
