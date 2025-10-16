# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment


class WebsiteOjtRecruitment(WebsiteHrRecruitment):
    _name = 'website.ojt.recruitment'
    _inherit = 'website.hr.recruitment'

    @http.route('/ojt/jobs', type='http', auth="public", website=True)
    def ojt_jobs(self, **kwargs):
        """OJT-specific job listings page"""
        # Get only jobs that have OJT batches
        ojt_jobs = request.env['hr.job'].sudo().search([
            ('website_id', 'in', [request.website.id, False])
        ])
        # Filter jobs that have active OJT batches
        ojt_jobs = ojt_jobs.filtered(lambda job: request.env['ojt.batch'].sudo().search_count([
            ('job_id', '=', job.id),
            ('state', 'in', ['recruit', 'ongoing']),
            ('active', '=', True)
        ]) > 0)

        # Get active OJT batches
        active_batches = request.env['ojt.batch'].sudo().search([
            ('state', 'in', ['recruit', 'ongoing']),
            ('active', '=', True)
        ])

        return request.render('ojt_batch_management.ojt_jobs', {
            'jobs': ojt_jobs,
            'batches': active_batches,
            'search': kwargs.get('search', ''),
        })

    @http.route('/ojt/jobs/<model("hr.job"):job>', type='http', auth="public", website=True)
    def ojt_job_detail(self, job, **kwargs):
        """OJT job detail page with batch selection"""
        # Get available batches for this job
        available_batches = request.env['ojt.batch'].sudo().search([
            ('job_id', '=', job.id),
            ('state', 'in', ['recruit', 'ongoing']),
            ('active', '=', True)
        ])

        return request.render('ojt_batch_management.ojt_job_detail', {
            'job': job,
            'available_batches': available_batches,
        })

    @http.route('/ojt/jobs/apply/<model("hr.job"):job>', type='http', auth="public", website=True, methods=['GET', 'POST'])
    def ojt_jobs_apply(self, job, **kwargs):
        """OJT application form with batch selection"""
        if request.httprequest.method == 'POST':
            return self._handle_ojt_application(job, **kwargs)

        # GET request - show form
        error = {}
        default = {}

        # Get available batches for this job
        available_batches = request.env['ojt.batch'].sudo().search([
            ('job_id', '=', job.id),
            ('state', 'in', ['recruit', 'ongoing']),
            ('active', '=', True)
        ])

        return request.render('ojt_batch_management.ojt_apply', {
            'job': job,
            'available_batches': available_batches,
            'error': error,
            'default': default,
        })

    def _handle_ojt_application(self, job, **kwargs):
        """Handle OJT application submission"""
        error = {}
        default = {}

        # Validate required fields
        required_fields = ['partner_name', 'email_from', 'ojt_batch_id']
        for field in required_fields:
            if not kwargs.get(field):
                error[field] = _("This field is required.")

        # Validate batch selection
        batch_id = kwargs.get('ojt_batch_id')
        if batch_id:
            try:
                batch = request.env['ojt.batch'].sudo().browse(int(batch_id))
                if not batch.exists() or batch.state not in ['recruit', 'ongoing']:
                    error['ojt_batch_id'] = _("Selected batch is not available.")
            except (ValueError, TypeError):
                error['ojt_batch_id'] = _("Invalid batch selection.")

        if error:
            # Return to form with errors
            available_batches = request.env['ojt.batch'].sudo().search([
                ('job_id', '=', job.id),
                ('state', 'in', ['recruit', 'ongoing']),
                ('active', '=', True)
            ])
            return request.render('ojt_batch_management.ojt_apply', {
                'job': job,
                'available_batches': available_batches,
                'error': error,
                'default': kwargs,
            })

        # Create or get candidate
        candidate_vals = {
            'partner_name': kwargs.get('partner_name'),
            'email_from': kwargs.get('email_from'),
            'partner_phone': kwargs.get('partner_phone', ''),
        }
        candidate = request.env['hr.candidate'].sudo().create(candidate_vals)

        # Create applicant with OJT batch
        applicant_vals = {
            'candidate_id': candidate.id,
            'job_id': job.id,
            'ojt_batch_id': int(batch_id),
        }

        # Handle file upload if present
        if 'resume' in request.httprequest.files:
            file = request.httprequest.files['resume']
            if file and file.filename:
                import base64
                applicant_vals['attachment_ids'] = [(0, 0, {
                    'name': file.filename,
                    'datas': base64.b64encode(file.read()).decode('utf-8'),
                    'res_model': 'hr.applicant',
                    'type': 'binary',
                })]

        applicant = request.env['hr.applicant'].sudo().create(applicant_vals)

        # Redirect to confirmation page
        return request.render('ojt_batch_management.ojt_application_submitted', {
            'applicant': applicant,
            'job': job,
        })

    @http.route('/ojt/batches', type='http', auth="public", website=True)
    def ojt_batches(self, **kwargs):
        """Public OJT batches listing"""
        batches = request.env['ojt.batch'].sudo().search([
            ('state', 'in', ['recruit', 'ongoing']),
            ('active', '=', True)
        ])

        return request.render('ojt_batch_management.ojt_batches', {
            'batches': batches,
        })

    @http.route('/ojt/batches/<model("ojt.batch"):batch>', type='http', auth="public", website=True)
    def ojt_batch_detail(self, batch, **kwargs):
        """OJT batch detail page"""
        return request.render('ojt_batch_management.ojt_batch_detail', {
            'batch': batch,
        })
