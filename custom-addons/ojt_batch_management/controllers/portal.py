# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

class OjtPortal(http.Controller):

    @http.route(['/my/ojt'], type='http', auth="user", website=True)
    def portal_my_ojt(self, **kw):
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        certificates = request.env['ojt.certificate'].sudo().search([
            ('participant_id.user_id', '=', request.env.user.id)
        ])
        assignments = request.env['ojt.assignment.submit'].sudo().search([
            ('participant_id.user_id', '=', request.env.user.id)
        ])
        progress_records = request.env['ojt.progress'].sudo().search([
            ('participant_id.user_id', '=', request.env.user.id)
        ])
        return request.render('ojt_batch_management.portal_ojt_dashboard', {
            'participant': participant,
            'certificates': certificates,
            'assignments': assignments,
            'progress_records': progress_records,
        })

    @http.route(['/my/ojt/certificate/<int:cert_id>/download'], type='http', auth="user", website=True)
    def portal_download_certificate(self, cert_id, **kw):
        cert = request.env['ojt.certificate'].sudo().search([('id', '=', cert_id)], limit=1)
        if not cert:
            return request.not_found()
        # security check: ensure current user is linked to the participant
        if cert.participant_id.user_id and cert.participant_id.user_id.id != request.env.user.id:
            raise AccessError("You are not allowed to access this certificate.")
        if not cert.pdf_file:
            # attempt to generate if missing
            cert.sudo().generate_pdf()
        data = cert.pdf_file
        if not data:
            return request.not_found()
        pdf = base64.b64decode(data)
        return request.make_response(pdf,
                                     headers=[('Content-Type', 'application/pdf'),
                                              ('Content-Disposition', f'attachment; filename={cert.pdf_filename or cert.name}.pdf')])
