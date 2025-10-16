{
    'name': 'OJT Batch Management',
    'version': '18.0.1.0',
    'author': 'Sandy Budi Wirawan',
    'category': 'Human Resources',
    'summary': 'Manage OJT Batches for Internship Programs',
    'depends': [
        'base',
        'mail',
        'portal',
        'contacts',
        'website',
        'hr_recruitment',
        'website_slides',
        'event',
        'survey',
        'calendar',
        'rating',
        'utm',
    ],
    'data': [
        # Security must come FIRST
        'security/ojt_security.xml',
        'security/ojt_security_rules.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/ojt_sequence.xml',
        'data/email_template_certificate.xml',
        'data/email_template_proctoring_scheduled.xml',
        
        # Reports
        'report/report_certificate.xml',
        'report/report_certificate_template.xml',
        'report/report_actions.xml',
        
        # Actions BEFORE menus
        'views/actions.xml',
        
        # Menus AFTER actions
        'views/menus.xml',
        
        # Other views
        'views/ojt_batch_views.xml',
        'views/ojt_participant_views.xml',
        'views/ojt_attendance_views.xml',
        'views/ojt_progress_views.xml',
        'views/ojt_certificate_views.xml',
        'views/ojt_assignment_views.xml',
        'views/ojt_assignment_submit_views.xml',
        'views/ojt_event_link_views.xml',
        
        # New feature views
        'views/ojt_meeting_attendance_views.xml',
        'views/ojt_gamification_views.xml',
        'views/ojt_proctoring_views.xml',

        # Portal templates last
        'views/certificate_verify_templates.xml',
        'views/portal/ojt_portal_templates.xml',
        'views/website_recruitment_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'ojt_batch_management/static/src/css/portal.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}