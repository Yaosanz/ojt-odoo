from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64


class OjtPortalPublic(http.Controller):

    @http.route('/ojt/cert/verify', type='http', auth='public', website=True)
    def certificate_verify(self, **kwargs):
        """Public certificate verification page"""
        serial = kwargs.get('serial', '').strip()
        qr_token = kwargs.get('qr', '').strip()

        certificate = None
        error_message = None

        if serial:
            certificate = request.env['ojt.certificate'].sudo().search([
                ('serial', '=', serial),
                ('state', '=', 'issued')
            ], limit=1)
            if not certificate:
                error_message = "Certificate not found or not issued."

        elif qr_token:
            certificate = request.env['ojt.certificate'].sudo().search([
                ('qr_token', '=', qr_token),
                ('state', '=', 'issued')
            ], limit=1)
            if not certificate:
                error_message = "Invalid QR code or certificate not issued."

        return request.render('ojt_batch_management.certificate_verify', {
            'certificate': certificate,
            'error_message': error_message,
            'serial': serial,
            'qr_token': qr_token,
        })

    @http.route('/ojt/cert/qr/<string:qr_token>', type='http', auth='public', website=True)
    def certificate_qr_redirect(self, qr_token):
        """Redirect QR code scans to verification page"""
        return request.redirect(f'/ojt/cert/verify?qr={qr_token}')

    @http.route('/ojt/attend/checkin', type='http', auth='public', methods=['GET', 'POST'], website=True)
    def attendance_checkin(self, **kwargs):
        """QR Code attendance check-in page"""
        qr_token = kwargs.get('qr', '').strip()
        event_link = None
        participant = None
        message = None
        message_type = 'info'

        if qr_token:
            # Decode QR token (format: event_id-participant_id-timestamp)
            try:
                parts = qr_token.split('-')
                if len(parts) >= 2:
                    event_id = int(parts[0])
                    participant_id = int(parts[1])

                    event_link = request.env['ojt.event.link'].sudo().browse(event_id)
                    participant = request.env['ojt.participant'].sudo().browse(participant_id)

                    if event_link.exists() and participant.exists():
                        # Check if already checked in
                        existing_attendance = request.env['ojt.attendance'].sudo().search([
                            ('event_link_id', '=', event_id),
                            ('participant_id', '=', participant_id),
                            ('date', '=', fields.Date.today())
                        ], limit=1)

                        if existing_attendance:
                            if existing_attendance.check_out:
                                message = "Already checked out for today."
                                message_type = 'warning'
                            else:
                                # Check out
                                existing_attendance.sudo().write({
                                    'check_out': fields.Datetime.now(),
                                    'presence': 'present'
                                })
                                message = f"Checked out successfully at {fields.Datetime.now().strftime('%H:%M')}."
                                message_type = 'success'
                        else:
                            # Check in
                            request.env['ojt.attendance'].sudo().create({
                                'event_link_id': event_id,
                                'participant_id': participant_id,
                                'date': fields.Date.today(),
                                'check_in': fields.Datetime.now(),
                                'presence': 'present',
                                'method': 'qr'
                            })
                            message = f"Checked in successfully at {fields.Datetime.now().strftime('%H:%M')}."
                            message_type = 'success'
                    else:
                        message = "Invalid QR code."
                        message_type = 'danger'
                else:
                    message = "Invalid QR code format."
                    message_type = 'danger'
            except (ValueError, IndexError):
                message = "Invalid QR code."
                message_type = 'danger'

        return request.render('ojt_batch_management.attendance_checkin', {
            'event_link': event_link,
            'participant': participant,
            'message': message,
            'message_type': message_type,
            'qr_token': qr_token,
        })

    @http.route('/ojt/cert/download/<int:cert_id>', type='http', auth='public')
    def certificate_download(self, cert_id):
        """Download certificate PDF"""
        certificate = request.env['ojt.certificate'].sudo().browse(cert_id)
        if certificate.exists() and certificate.state == 'issued' and certificate.pdf_file:
            pdf_data = base64.b64decode(certificate.pdf_file)
            filename = f"Certificate_{certificate.serial}.pdf"
            return request.make_response(pdf_data, headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ])
        return request.not_found()


class OjtPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if request.env.user.has_group('base.group_portal'):
            participant = request.env['ojt.participant'].sudo().search([
                ('user_id', '=', request.env.user.id)
            ], limit=1)
            if participant:
                values['ojt_participant'] = participant
                values['ojt_batch'] = participant.batch_id
        return values
