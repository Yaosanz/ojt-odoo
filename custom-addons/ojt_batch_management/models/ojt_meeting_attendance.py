# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta

class OjtMeetingAttendance(models.Model):
    _name = 'ojt.meeting.attendance'
    _description = 'OJT Meeting Attendance Integration'
    _inherit = ['mail.thread']

    name = fields.Char(string='Meeting Name', required=True)
    event_link_id = fields.Many2one('ojt.event.link', string='Event Link', required=True)
    proctor_id = fields.Many2one('res.users', string='Proctor', required=True, default=lambda self: self.env.user, tracking=True)
    platform = fields.Selection([
        ('teams', 'Microsoft Teams'),
        ('zoom', 'Zoom'),
        ('meet', 'Google Meet')
    ], string='Platform', required=True)
    meeting_id = fields.Char(string='Meeting ID/URL')
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    min_duration = fields.Float(string='Minimum Duration (minutes)', default=30)
    attendee_ids = fields.One2many('ojt.meeting.attendee', 'meeting_id', string='Attendees')
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='scheduled', tracking=True)
    api_key = fields.Char(string='API Key', help='API Key for the meeting platform')
    api_secret = fields.Char(string='API Secret')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    def action_fetch_attendance(self):
        """Fetch attendance data from the meeting platform"""
        if not self.meeting_id or not self.api_key:
            return False
        if self.platform == 'teams':
            return self._fetch_teams_attendance()
        elif self.platform == 'zoom':
            return self._fetch_zoom_attendance()
        elif self.platform == 'meet':
            return self._fetch_meet_attendance()

    def _fetch_teams_attendance(self):
        """Fetch attendance data from Microsoft Teams"""
        pass

    def _fetch_zoom_attendance(self):
        """Fetch attendance data from Zoom"""
        pass

    def _fetch_meet_attendance(self):
        """Fetch attendance data from Google Meet"""
        pass

    @api.model
    def _cron_sync_meeting_attendance(self):
        """Cron job to sync meeting attendance data"""
        meetings = self.search([
            ('state', 'in', ['ongoing', 'scheduled']),
            ('start_time', '<=', fields.Datetime.now()),
            ('end_time', '>=', fields.Datetime.now() - timedelta(hours=24))
        ])
        for meeting in meetings:
            meeting.action_fetch_attendance()


class OjtMeetingAttendee(models.Model):
    _name = 'ojt.meeting.attendee'
    _description = 'OJT Meeting Attendee'

    meeting_id = fields.Many2one('ojt.meeting.attendance', string='Meeting', required=True)
    participant_id = fields.Many2one('ojt.participant', string='Participant')
    join_time = fields.Datetime(string='Join Time')
    leave_time = fields.Datetime(string='Leave Time')
    duration = fields.Float(string='Duration (minutes)', compute='_compute_duration', store=True)
    attendance_status = fields.Selection([
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent')
    ], string='Status', compute='_compute_status', store=True)

    @api.depends('join_time', 'leave_time')
    def _compute_duration(self):
        for record in self:
            if record.join_time and record.leave_time:
                delta = record.leave_time - record.join_time
                record.duration = delta.total_seconds() / 60
            else:
                record.duration = 0

    @api.depends('duration', 'meeting_id.min_duration')
    def _compute_status(self):
        for record in self:
            if not record.join_time:
                record.attendance_status = 'absent'
            elif record.duration >= record.meeting_id.min_duration:
                record.attendance_status = 'present'
            else:
                record.attendance_status = 'late'
