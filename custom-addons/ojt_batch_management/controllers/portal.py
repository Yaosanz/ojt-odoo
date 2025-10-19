# -*- coding: utf-8 -*-
import base64
import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

class OjtPortal(http.Controller):

    @http.route(['/my/ojt'], type='http', auth="user", website=True)
    def portal_my_ojt(self, **kw):
        # cari participant berdasarkan user_id terlebih dahulu
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        # fallback: cari berdasarkan partner_id jika user_id tidak di ukan
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

        # Get available assignments (not yet submitted)
        available_assignments = []
        if participant:
            submitted_assignment_ids = [a.assignment_id.id for a in assignments]
            available_assignments = request.env['ojt.assignment'].sudo().search([
                ('batch_id', '=', participant.batch_id.id),
                ('id', 'not in', submitted_assignment_ids)
            ])

        # Get available certificates (not yet issued)
        available_certificates = []
        if participant:
            issued_certificate_ids = [c.id for c in certificates]
            available_certificates = request.env['ojt.certificate'].sudo().search([
                ('participant_id', '=', participant.id),
                ('id', 'not in', issued_certificate_ids),
                ('state', 'in', ['draft', 'pending'])
            ])

        attendances = request.env['ojt.attendance'].sudo().search([
            ('participant_id', '=', participant.id)
        ]) if participant else []

        progress_records = request.env['ojt.progress'].sudo().search([
            ('participant_id', '=', participant.id)
        ]) if participant else []

        # Get upcoming events for check-in
        upcoming_events = []
        if participant:
            from datetime import datetime
            now = datetime.now()
            event_links = request.env['ojt.event.link'].sudo().search([
                ('batch_id', '=', participant.batch_id.id),
                ('event_id.date_begin', '>=', now)
            ])
            for event_link in event_links:
                # Check if participant hasn't checked in yet
                existing_attendance = request.env['ojt.attendance'].sudo().search([
                    ('participant_id', '=', participant.id),
                    ('event_link_id', '=', event_link.id)
                ], limit=1)
                if not existing_attendance:
                    upcoming_events.append(event_link)

        # Handle success/error messages from URL parameters
        success_message = kw.get('success')
        error_message = kw.get('error')

        return request.render('ojt_batch_management.portal_ojt_dashboard', {
            'participant': participant,
            'certificates': certificates,
            'assignments': assignments,
            'available_assignments': available_assignments,
            'available_certificates': available_certificates,
            'attendances': attendances,
            'progress_records': progress_records,
            'upcoming_events': upcoming_events,
            'success': success_message,
            'error': error_message,
        })

    @http.route(['/my/ojt/certificate/<int:cert_id>/download'], type='http', auth="user", website=True)
    def portal_download_certificate(self, cert_id, **kw):
        # Ambil record sertifikat
        cert = request.env['ojt.certificate'].sudo().browse(cert_id)
        if not cert.exists():
            return request.not_found()

        # Validasi hak akses: hanya peserta pemilik yang boleh download
        user = request.env.user
        participant = cert.participant_id

        allowed = False
        if participant:
            if participant.user_id and participant.user_id.id == user.id:
                allowed = True
            elif participant.partner_id and participant.partner_id.id == user.partner_id.id:
                allowed = True

        if not allowed:
            return request.not_found()

        # Buat PDF jika belum ada
        if not cert.pdf_file and hasattr(cert, 'generate_pdf'):
            try:
                cert.sudo().generate_pdf()
            except Exception as e:
                # Gunakan Python logger, bukan ir.logging
                _logger.error(
                    "Gagal generate PDF untuk Certificate ID %s. Error: %s",
                    cert_id,
                    str(e)
                )
                return request.not_found()

        # Pastikan file PDF sudah ada
        if not cert.pdf_file:
            return request.not_found()

        # Decode file PDF
        try:
            pdf = base64.b64decode(cert.pdf_file)
        except Exception as e:
            _logger.error(
                "Gagal decode PDF untuk Certificate ID %s. Error: %s",
                cert_id,
                str(e)
            )
            return request.not_found()

        # Sanitasi nama file agar tidak error di browser
        raw_name = cert.pdf_filename or cert.name or "certificate"
        filename = "".join(
            c if c.isalnum() or c in ('_', '-') else "_" for c in raw_name
        ) + ".pdf"

        # Return response file PDF
        return request.make_response(
            pdf,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )

    @http.route(['/my/ojt/assignment/<int:assignment_id>'], type='http', auth="user", website=True)
    def portal_assignment_view(self, assignment_id, **kw):
        assignment = request.env['ojt.assignment'].sudo().browse(assignment_id)
        if not assignment.exists():
            return request.not_found()

        # Check if user has access to this assignment (through participant)
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant or assignment.batch_id != participant.batch_id:
            return request.not_found()

        # Get submission for this assignment
        submission = request.env['ojt.assignment.submit'].sudo().search([
            ('assignment_id', '=', assignment_id),
            ('participant_id', '=', participant.id)
        ], limit=1)

        # Handle success/error messages from URL parameters
        success_message = kw.get('success')
        error_message = kw.get('error')

        return request.render('ojt_batch_management.portal_ojt_assignment_view', {
            'assignment': assignment,
            'submission': submission,
            'participant': participant,
            'success': success_message,
            'error': error_message,
        })

    @http.route(['/my/ojt/attendance/<int:attendance_id>'], type='http', auth="user", website=True)
    def portal_attendance_view(self, attendance_id, **kw):
        attendance = request.env['ojt.attendance'].sudo().browse(attendance_id)
        if not attendance.exists():
            return request.not_found()

        # Check if user has access to this attendance
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant or attendance.participant_id != participant:
            return request.not_found()

        return request.render('ojt_batch_management.portal_ojt_attendance_view', {
            'attendance': attendance,
            'participant': participant,
        })

    @http.route(['/my/ojt/progress/<int:progress_id>'], type='http', auth="user", website=True)
    def portal_progress_view(self, progress_id, **kw):
        progress = request.env['ojt.progress'].sudo().browse(progress_id)
        if not progress.exists():
            return request.not_found()

        # Check if user has access to this progress record
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant or progress.participant_id != participant:
            return request.not_found()

        return request.render('ojt_batch_management.portal_ojt_progress_view', {
            'progress': progress,
            'participant': participant,
        })

    @http.route(['/my/ojt/submission/<int:submission_id>'], type='http', auth="user", website=True)
    def portal_submission_view(self, submission_id, **kw):
        submission = request.env['ojt.assignment.submit'].sudo().browse(submission_id)
        if not submission.exists():
            return request.not_found()

        # Check if user has access to this submission
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant or submission.participant_id != participant:
            return request.not_found()

        return request.render('ojt_batch_management.portal_ojt_submission_view', {
            'submission': submission,
            'participant': participant,
        })

    @http.route(['/my/ojt/assignment/submit'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_assignment_submit(self, **kw):
        assignment_id = kw.get('assignment_id')
        if not assignment_id:
            return request.redirect('/my/ojt?error=missing_assignment')

        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant:
            return request.redirect('/my/ojt?error=no_participant')

        # Get assignment
        assignment = request.env['ojt.assignment'].sudo().browse(int(assignment_id))
        if not assignment.exists() or assignment.batch_id != participant.batch_id:
            return request.redirect('/my/ojt?error=invalid_assignment')

        # Check if already submitted
        existing_submission = request.env['ojt.assignment.submit'].sudo().search([
            ('assignment_id', '=', assignment.id),
            ('participant_id', '=', participant.id)
        ], limit=1)

        if existing_submission:
            return request.redirect(f'/my/ojt/assignment/{assignment.id}?error=already_submitted')

        # Handle file uploads
        attachment_ids = []
        if request.httprequest.files:
            for file_key, file_storage in request.httprequest.files.items():
                if file_key.startswith('attachment') and file_storage.filename:
                    attachment_vals = {
                        'name': file_storage.filename,
                        'datas': base64.b64encode(file_storage.read()),
                        'res_model': 'ojt.assignment.submit',
                        'res_id': 0,  # Will be updated after submission creation
                    }
                    attachment = request.env['ir.attachment'].sudo().create(attachment_vals)
                    attachment_ids.append(attachment.id)

        # Create submission
        submission_vals = {
            'assignment_id': assignment.id,
            'participant_id': participant.id,
            'url_link': kw.get('url_link'),
            'attachment_ids': [(6, 0, attachment_ids)],
        }

        try:
            submission = request.env['ojt.assignment.submit'].sudo().create(submission_vals)

            # Update attachment res_id
            if attachment_ids:
                request.env['ir.attachment'].sudo().browse(attachment_ids).write({
                    'res_id': submission.id
                })

            return request.redirect(f'/my/ojt/assignment/{assignment.id}?success=submitted')
        except Exception as e:
            return request.redirect(f'/my/ojt/assignment/{assignment.id}?error=submit_failed')

    @http.route(['/my/ojt/attendance/checkout'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_attendance_checkout(self, **kw):
        attendance_id = kw.get('attendance_id')
        if not attendance_id:
            return request.redirect('/my/ojt?error=missing_attendance')

        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant:
            return request.redirect('/my/ojt?error=no_participant')

        # Get attendance record
        attendance = request.env['ojt.attendance'].sudo().browse(int(attendance_id))
        if not attendance.exists() or attendance.participant_id != participant:
            return request.redirect('/my/ojt?error=invalid_attendance')

        # Check if already checked out
        if attendance.check_out:
            return request.redirect(f'/my/ojt/attendance/{attendance.id}?error=already_checked_out')

        # Update attendance with check-out time
        from datetime import datetime
        now = datetime.now()

        try:
            attendance.sudo().write({'check_out': now})
            return request.redirect(f'/my/ojt/attendance/{attendance.id}?success=checked_out')
        except Exception as e:
            return request.redirect(f'/my/ojt/attendance/{attendance.id}?error=checkout_failed')

    @http.route(['/my/ojt/progress/update'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_progress_update(self, **kw):
        progress_id = kw.get('progress_id')
        if not progress_id:
            return request.redirect('/my/ojt?error=missing_progress')

        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant:
            return request.redirect('/my/ojt?error=no_participant')

        # Get progress record
        progress = request.env['ojt.progress'].sudo().browse(int(progress_id))
        if not progress.exists() or progress.participant_id != participant:
            return request.redirect('/my/ojt?error=invalid_progress')

        # Update progress
        progress_vals = {
            'description': kw.get('description'),
            'progress_percentage': float(kw.get('progress_percentage', 0)),
        }

        try:
            progress.sudo().write(progress_vals)
            return request.redirect(f'/my/ojt/progress/{progress.id}?success=progress_updated')
        except Exception as e:
            return request.redirect(f'/my/ojt/progress/{progress.id}?error=progress_update_failed')

    @http.route(['/my/ojt/submission/feedback'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_submission_feedback(self, **kw):
        submission_id = kw.get('submission_id')
        if not submission_id:
            return request.redirect('/my/ojt?error=missing_submission')

        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant:
            return request.redirect('/my/ojt?error=no_participant')

        # Get submission
        submission = request.env['ojt.assignment.submit'].sudo().browse(int(submission_id))
        if not submission.exists() or submission.participant_id != participant:
            return request.redirect('/my/ojt?error=invalid_submission')

        # Check if feedback already exists
        if submission.feedback:
            return request.redirect(f'/my/ojt/submission/{submission.id}?error=feedback_already_exists')

        # Add participant feedback
        feedback_vals = {
            'participant_feedback': kw.get('participant_feedback'),
        }

        try:
            submission.sudo().write(feedback_vals)
            return request.redirect(f'/my/ojt/submission/{submission.id}?success=feedback_submitted')
        except Exception as e:
            return request.redirect(f'/my/ojt/submission/{submission.id}?error=feedback_failed')

    @http.route(['/my/ojt/certificate/request'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_certificate_request(self, **kw):
        certificate_id = kw.get('certificate_id')
        if not certificate_id:
            return request.redirect('/my/ojt?error=missing_certificate')

        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant:
            return request.redirect('/my/ojt?error=no_participant')

        # Get certificate
        certificate = request.env['ojt.certificate'].sudo().browse(int(certificate_id))
        if not certificate.exists() or certificate.participant_id != participant:
            return request.redirect('/my/ojt?error=invalid_certificate')

        # Check if already issued
        if certificate.state == 'issued':
            return request.redirect(f'/my/ojt/certificate/{certificate.id}?error=certificate_already_issued')

        # Update certificate with request notes
        request_vals = {
            'remarks': kw.get('request_notes', ''),
        }

        try:
            certificate.sudo().write(request_vals)
            return request.redirect(f'/my/ojt/certificate/{certificate.id}?success=certificate_requested')
        except Exception as e:
            return request.redirect(f'/my/ojt/certificate/{certificate.id}?error=certificate_request_failed')

    @http.route(['/my/ojt/events'], type='http', auth="user", website=True)
    def portal_events_page(self, **kw):
        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        # Get all events for the participant's batch
        events = []
        if participant:
            events = request.env['ojt.event.link'].sudo().search([
                ('batch_id', '=', participant.batch_id.id)
            ], order='event_date desc')

        return request.render('ojt_batch_management.portal_ojt_events', {
            'participant': participant,
            'events': events,
        })

    @http.route(['/my/ojt/attendance'], type='http', auth="user", website=True)
    def portal_attendance_records_page(self, **kw):
        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        # Get attendance records
        attendances = request.env['ojt.attendance'].sudo().search([
            ('participant_id', '=', participant.id)
        ], order='check_in desc') if participant else []

        return request.render('ojt_batch_management.portal_ojt_attendance_records', {
            'participant': participant,
            'attendances': attendances,
        })

    @http.route(['/my/ojt/meeting'], type='http', auth="user", website=True)
    def portal_meeting_attendance_page(self, **kw):
        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        # Get meeting attendance records
        meeting_attendances = []
        if participant:
            # Get all meeting attendances for the participant's batch
            meetings = request.env['ojt.meeting.attendance'].sudo().search([
                ('event_link_id.batch_id', '=', participant.batch_id.id)
            ], order='start_time desc')

            # Filter to only include meetings where the participant has attendance data
            for meeting in meetings:
                attendee = meeting.attendee_ids.filtered(lambda a: a.participant_id == participant)
                if attendee:
                    # Attach the attendee data to the meeting for template access
                    meeting.participant_attendee = attendee[0] if attendee else False
                    meeting_attendances.append(meeting)

        return request.render('ojt_batch_management.portal_ojt_meeting_attendance', {
            'participant': participant,
            'meeting_attendances': meeting_attendances,
        })

    @http.route(['/my/ojt/assignments'], type='http', auth="user", website=True)
    def portal_assignments_page(self, **kw):
        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        # Get assignments data
        assignments = request.env['ojt.assignment.submit'].sudo().search([
            ('participant_id', '=', participant.id)
        ], order='submitted_on desc') if participant else []

        # Get available assignments (not yet submitted)
        available_assignments = []
        if participant:
            submitted_assignment_ids = [a.assignment_id.id for a in assignments]
            available_assignments = request.env['ojt.assignment'].sudo().search([
                ('batch_id', '=', participant.batch_id.id),
                ('id', 'not in', submitted_assignment_ids)
            ], order='deadline asc')

        return request.render('ojt_batch_management.portal_ojt_assignments', {
            'participant': participant,
            'assignments': assignments,
            'available_assignments': available_assignments,
        })

    @http.route(['/my/ojt/attendance/checkin'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_attendance_checkin(self, **kw):
        event_link_id = kw.get('event_link_id')
        if not event_link_id:
            return request.redirect('/my/ojt?error=missing_event')

        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not participant:
            participant = request.env['ojt.participant'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        if not participant:
            return request.redirect('/my/ojt?error=no_participant')

        # Get event link
        event_link = request.env['ojt.event.link'].sudo().browse(int(event_link_id))
        if not event_link.exists() or event_link.batch_id != participant.batch_id:
            return request.redirect('/my/ojt?error=invalid_event')

        # Check if already checked in
        existing_attendance = request.env['ojt.attendance'].sudo().search([
            ('participant_id', '=', participant.id),
            ('event_link_id', '=', event_link.id)
        ], limit=1)

        if existing_attendance:
            return request.redirect('/my/ojt?error=already_checked_in')

        # Create attendance record
        from datetime import datetime
        now = datetime.now()

        attendance_vals = {
            'participant_id': participant.id,
            'event_link_id': event_link.id,
            'check_in': now,
            'presence': 'present',
            'method': 'online',  # Since it's portal check-in
        }

        # Check if late
        if event_link.event_id and event_link.event_id.date_begin:
            event_start = event_link.event_id.date_begin
            if now > event_start:
                # Calculate if more than 15 minutes late
                time_diff = (now - event_start).total_seconds() / 60
                if time_diff > 15:
                    attendance_vals['presence'] = 'late'

        try:
            request.env['ojt.attendance'].sudo().create(attendance_vals)
            return request.redirect('/my/ojt?success=checked_in')
        except Exception as e:
            return request.redirect('/my/ojt?error=checkin_failed')
