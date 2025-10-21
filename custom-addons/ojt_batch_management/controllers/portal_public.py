# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64
import logging

_logger = logging.getLogger(__name__)


class OjtPortalPublic(http.Controller):

    @http.route('/ojt/cert/verify', type='http', auth='public', website=True)
    def certificate_verify(self, **kwargs):
        """Public certificate verification page"""
        serial = kwargs.get('serial', '').strip()
        error_param = kwargs.get('error', '')

        certificate = None
        error_message = None

        if error_param == 'invalid_qr':
            error_message = "Invalid QR code. Certificate not found."
        elif serial:
            result = request.env['ojt.certificate'].sudo().verify_certificate(serial)
            if result['valid']:
                certificate = request.env['ojt.certificate'].sudo().search([
                    ('serial', '=', serial),
                    ('state', '=', 'issued')
                ], limit=1)
            else:
                error_message = "Certificate not found or not issued."

        return request.render('ojt_batch_management.certificate_verify', {
            'certificate': certificate,
            'error_message': error_message,
            'serial': serial,
        })

    @http.route('/ojt/cert/qr/<string:qr_token>', type='http', auth='public', website=True)
    def certificate_qr_redirect(self, qr_token):
        """Redirect QR code scans to verification page"""
        certificate = request.env['ojt.certificate'].sudo().search([('qr_token', '=', qr_token)], limit=1)
        if certificate and certificate.state == 'issued':
            return request.redirect(f'/ojt/cert/verify?serial={certificate.serial}')
        return request.redirect('/ojt/cert/verify?error=invalid_qr')

    @http.route('/ojt/attend/checkin', type='http', auth='public', methods=['GET', 'POST'], website=True)
    def attendance_checkin(self, **kwargs):
        """QR Code attendance check-in page"""
        qr_token = kwargs.get('qr', '').strip()
        event_link = None
        participant = None
        message = None
        message_type = 'info'

        if qr_token:
            try:
                parts = qr_token.split('-')
                if len(parts) >= 2:
                    event_id = int(parts[0])
                    participant_id = int(parts[1])

                    event_link = request.env['ojt.event.link'].sudo().browse(event_id)
                    participant = request.env['ojt.participant'].sudo().browse(participant_id)

                    if event_link.exists() and participant.exists():
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
                                existing_attendance.sudo().write({
                                    'check_out': fields.Datetime.now(),
                                    'presence': 'present'
                                })
                                message = f"Checked out successfully at {fields.Datetime.now().strftime('%H:%M')}."
                                message_type = 'success'
                        else:
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

    # 🔹 QR Tool Page
    @http.route('/ojt/qr/tool', type='http', auth='public', website=True)
    def qr_tool_page(self, **kwargs):
        """Public page for QR Code Generator & Scanner"""
        return request.render('ojt_batch_management.qr_tool_page', {})

    # 🔹 Forgot Password Page
    @http.route('/ojt/forgot-password', type='http', auth='public', website=True, methods=['GET', 'POST'])
    def forgot_password(self, **kwargs):
        """Forgot password page for OJT participants"""
        error = None
        success = None

        if request.httprequest.method == 'POST':
            email = kwargs.get('email', '').strip()
            if not email:
                error = "Please enter your email address."
            else:
                # Check if email exists in participants
                participant = request.env['ojt.participant'].sudo().search([
                    ('partner_id.email', '=', email),
                    ('state', 'in', ['active', 'completed'])
                ], limit=1)

                if participant and participant.user_id:
                    try:
                        # Send password reset email
                        participant.user_id.sudo().action_reset_password()
                        success = "Password reset instructions have been sent to your email."
                        _logger.info(f"Password reset requested for participant {participant.id} ({email})")
                    except Exception as e:
                        _logger.error(f"Failed to send password reset for {email}: {e}")
                        error = "Failed to send password reset email. Please try again."
                else:
                    # Don't reveal if email exists or not for security
                    success = "If your email is registered, password reset instructions have been sent."

        return request.render('ojt_batch_management.forgot_password', {
            'error': error,
            'success': success,
        })

    # 🔹 Sign Up Page
    @http.route('/ojt/signup', type='http', auth='public', website=True, methods=['GET', 'POST'])
    def ojt_signup(self, **kwargs):
        """OJT participant signup page"""
        error = {}
        success = None

        if request.httprequest.method == 'POST':
            # Validate required fields
            name = kwargs.get('name', '').strip()
            email = kwargs.get('email', '').strip()
            phone = kwargs.get('phone', '').strip()
            batch_id = kwargs.get('batch_id', '').strip()

            if not name:
                error['name'] = "Name is required."
            if not email:
                error['email'] = "Email is required."
            elif not self._is_valid_email(email):
                error['email'] = "Please enter a valid email address."
            if not batch_id:
                error['batch_id'] = "Please select an OJT batch."

            # Check if email already exists
            if email:
                existing_user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
                existing_participant = request.env['ojt.participant'].sudo().search([
                    ('partner_id.email', '=', email)
                ], limit=1)

                if existing_user or existing_participant:
                    error['email'] = "This email is already registered."

            if not error:
                try:
                    # Create partner
                    partner_vals = {
                        'name': name,
                        'email': email,
                        'phone': phone,
                    }
                    partner = request.env['res.partner'].sudo().create(partner_vals)

                    # Create participant
                    participant_vals = {
                        'partner_id': partner.id,
                        'batch_id': int(batch_id),
                        'state': 'draft',  # Will be activated after email verification
                    }
                    participant = request.env['ojt.participant'].sudo().create(participant_vals)

                    # Send activation email
                    self._send_activation_email(participant)

                    success = "Registration successful! Please check your email for activation instructions."
                    _logger.info(f"New OJT participant registered: {participant.id} ({email})")

                except Exception as e:
                    _logger.error(f"Failed to register participant {email}: {e}")
                    error['general'] = "Registration failed. Please try again."

        # Get available batches
        available_batches = request.env['ojt.batch'].sudo().search([
            ('state', 'in', ['recruit', 'ongoing']),
            ('active', '=', True)
        ])

        return request.render('ojt_batch_management.signup', {
            'error': error,
            'success': success,
            'available_batches': available_batches,
        })

    # 🔹 Email Activation
    @http.route('/ojt/activate/<string:token>', type='http', auth='public', website=True)
    def activate_account(self, token, **kwargs):
        """Activate participant account via email link"""
        participant = request.env['ojt.participant'].sudo().search([
            ('portal_token', '=', token),
            ('state', '=', 'draft')
        ], limit=1)

        if not participant:
            return request.render('ojt_batch_management.activation_result', {
                'success': False,
                'message': "Invalid or expired activation link."
            })

        try:
            # Activate participant and create user
            participant.sudo().write({'state': 'active'})

            # Create portal user if not exists
            if not participant.user_id and participant.partner_id.email:
                group_portal = request.env.ref('base.group_portal')
                existing_user = request.env['res.users'].sudo().search([
                    ('login', '=', participant.partner_id.email)
                ], limit=1)

                if not existing_user:
                    user_vals = {
                        'name': participant.partner_id.name,
                        'login': participant.partner_id.email,
                        'email': participant.partner_id.email,
                        'partner_id': participant.partner_id.id,
                        'groups_id': [(6, 0, [group_portal.id])],
                    }
                    user = request.env['res.users'].sudo().create(user_vals)

                    # Send welcome email with login details
                    self._send_welcome_email(user, participant)

            _logger.info(f"Participant account activated: {participant.id}")

            return request.render('ojt_batch_management.activation_result', {
                'success': True,
                'message': "Your account has been successfully activated! You can now log in.",
                'login_url': '/web/login',
            })

        except Exception as e:
            _logger.error(f"Failed to activate participant {participant.id}: {e}")
            return request.render('ojt_batch_management.activation_result', {
                'success': False,
                'message': "Activation failed. Please contact support."
            })

    def _is_valid_email(self, email):
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _send_activation_email(self, participant):
        """Send account activation email"""
        try:
            template = request.env.ref('ojt_batch_management.email_template_ojt_activation')
            template.sudo().send_mail(participant.id, force_send=True)
        except Exception as e:
            _logger.error(f"Failed to send activation email to {participant.partner_id.email}: {e}")

    def _send_welcome_email(self, user, participant):
        """Send welcome email with login details"""
        try:
            template = request.env.ref('ojt_batch_management.email_template_ojt_welcome')
            template.sudo().send_mail(participant.id, force_send=True)
        except Exception as e:
            _logger.error(f"Failed to send welcome email to {user.email}: {e}")


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
