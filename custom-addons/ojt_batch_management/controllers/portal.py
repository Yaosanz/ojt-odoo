# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

class OjtPortal(http.Controller):

    @http.route(['/my/ojt'], type='http', auth="user", website=True)
    def portal_my_ojt(self, **kw):
        # cari participant berdasarkan user_id terlebih dahulu
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        # fallback: cari berdasarkan partner_id jika user_id tidak ditemukan
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        # ambil data terkait jika participant ditemukan
        certificates = request.env['ojt.certificate'].sudo().search([
            ('participant_id', '=', participant.id)
        ]) if participant else []

        assignments = request.env['ojt.assignment.submit'].sudo().search([
            ('participant_id', '=', participant.id)
        ]) if participant else []

        progress_records = request.env['ojt.progress'].sudo().search([
            ('participant_id', '=', participant.id)
        ]) if participant else []

        return request.render('ojt_batch_management.portal_ojt_dashboard', {
            'participant': participant,
            'certificates': certificates,
            'assignments': assignments,
            'progress_records': progress_records,
        })

    @http.route(['/my/ojt/certificate/<int:cert_id>/download'], type='http', auth="user", website=True)
    def portal_download_certificate(self, cert_id, **kw):
        # gunakan browse untuk efisiensi
        cert = request.env['ojt.certificate'].sudo().browse(cert_id)
        if not cert.exists():
            return request.not_found()

        # keamanan: hanya peserta pemilik yang boleh download
        user = request.env.user
        participant = cert.participant_id

        allowed = False
        if participant:
            if participant.user_id:
                allowed = (participant.user_id.id == user.id)
            elif participant.partner_id:
                allowed = (participant.partner_id.id == user.partner_id.id)

        if not allowed:
            # Untuk portal user, tampilkan 404 agar tidak bocor info
            return request.not_found()

        # Generate PDF jika belum ada
        if not cert.pdf_file:
            if hasattr(cert, 'generate_pdf'):
                try:
                    cert.sudo().generate_pdf()
                except Exception:
                    return request.not_found()

        if not cert.pdf_file:
            return request.not_found()

        pdf = base64.b64decode(cert.pdf_file)
        filename = (cert.pdf_filename or cert.name or "certificate").replace(" ", "_") + ".pdf"

        return request.make_response(
            pdf,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )