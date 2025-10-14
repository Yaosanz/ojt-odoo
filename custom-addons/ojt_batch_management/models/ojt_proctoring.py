# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import base64
from datetime import datetime, timedelta

class OjtQuizProctoring(models.Model):
    _name = 'ojt.quiz.proctoring'
    _description = 'OJT Quiz Proctoring'
    _inherit = ['mail.thread']

    name = fields.Char(string='Session Name', required=True)
    survey_id = fields.Many2one('survey.survey', string='Quiz/Survey', required=True)
    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', required=True)
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string='Duration (minutes)', default=60)
    proctor_id = fields.Many2one('res.users', string='Proctor', required=True)
    participant_ids = fields.Many2many('ojt.participant', string='Participants')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    proctoring_settings = fields.Selection([
        ('basic', 'Basic (Screenshot + Webcam)'),
        ('advanced', 'Advanced (Full Browser Lock)')
    ], string='Proctoring Level', default='basic', required=True)
    webcam_required = fields.Boolean(string='Webcam Required', default=True)
    screenshot_interval = fields.Integer(string='Screenshot Interval (seconds)', default=60)
    browser_lock = fields.Boolean(string='Enable Browser Lock', default=False)
    violation_count = fields.Integer(compute='_compute_violations', store=True)
    session_logs = fields.One2many('ojt.proctoring.log', 'session_id', string='Session Logs')

    @api.model
    def create(self, vals):
        """Create proctoring session and configure survey settings"""
        res = super().create(vals)
        if res.survey_id:
            res.survey_id.write({
                'is_time_limited': True,
                'time_limit': res.duration
            })
        return res

    def action_schedule(self):
        """Schedule the proctoring session"""
        self.write({'state': 'scheduled'})
        # Send notifications to participants
        template = self.env.ref('ojt_batch_management.email_template_proctoring_scheduled')
        for participant in self.participant_ids:
            template.send_mail(participant.id)

    def action_start(self):
        """Start the proctoring session"""
        if fields.Datetime.now() < self.start_time:
            raise UserError("Cannot start session before scheduled time")
        self.write({'state': 'ongoing'})

    def action_end(self):
        """End the proctoring session"""
        self.write({'state': 'completed'})
        self._process_violations()

    def _process_violations(self):
        """Process violations and adjust scores if necessary"""
        for participant in self.participant_ids:
            violations = self.env['ojt.proctoring.log'].search_count([
                ('session_id', '=', self.id),
                ('participant_id', '=', participant.id),
                ('violation_type', '!=', False)
            ])
            if violations > 0:
                # Adjust score based on violations
                survey_response = self.env['survey.user_input'].search([
                    ('survey_id', '=', self.survey_id.id),
                    ('partner_id', '=', participant.partner_id.id)
                ], limit=1)
                if survey_response:
                    penalty = min(violations * 5, 100)  # 5% penalty per violation, max 100%
                    new_score = survey_response.scoring_percentage * (100 - penalty) / 100
                    survey_response.write({'scoring_percentage': new_score})

    @api.depends('session_logs.violation_type')
    def _compute_violations(self):
        """Compute the number of violations in the session"""
        for record in self:
            record.violation_count = len(record.session_logs.filtered(lambda l: l.violation_type))

class OjtProctoringLog(models.Model):
    _name = 'ojt.proctoring.log'
    _description = 'OJT Proctoring Log'
    _order = 'timestamp desc'

    session_id = fields.Many2one('ojt.quiz.proctoring', string='Proctoring Session', required=True)
    participant_id = fields.Many2one('ojt.participant', string='Participant', required=True)
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now)
    event_type = fields.Selection([
        ('join', 'Joined Session'),
        ('leave', 'Left Session'),
        ('screenshot', 'Screenshot Taken'),
        ('webcam', 'Webcam Capture'),
        ('violation', 'Violation Detected')
    ], string='Event Type')
    violation_type = fields.Selection([
        ('tab_switch', 'Tab Switching'),
        ('multiple_faces', 'Multiple Faces Detected'),
        ('no_face', 'No Face Detected'),
        ('browser_resize', 'Browser Resized'),
        ('copy_paste', 'Copy-Paste Detected')
    ], string='Violation Type')
    snapshot = fields.Binary(string='Snapshot', attachment=True)
    details = fields.Text(string='Event Details')

    def record_violation(self, violation_type, details=None):
        """Record a proctoring violation"""
        self.create({
            'event_type': 'violation',
            'violation_type': violation_type,
            'details': details
        })
        # Notify proctor in real-time
        self.session_id.proctor_id.notify_info(
            message=f'Violation detected: {violation_type}',
            title='Proctoring Alert'
        )