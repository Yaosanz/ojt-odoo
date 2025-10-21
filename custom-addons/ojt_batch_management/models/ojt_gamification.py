# -*- coding: utf-8 -*-
from odoo import models, fields, api

class OjtGamification(models.Model):
    _name = 'ojt.gamification'
    _description = 'OJT Gamification'
    _inherit = ['mail.thread']

    name = fields.Char(string='Badge Name', required=True)
    description = fields.Text(string='Description')
    points = fields.Integer(string='Points', default=10)
    badge_type = fields.Selection([
        ('attendance', 'Perfect Attendance'),
        ('assignment', 'Assignment Excellence'),
        ('participation', 'Active Participation'),
        ('leadership', 'Leadership'),
        ('innovation', 'Innovation'),
        ('teamwork', 'Teamwork')
    ], string='Badge Type', required=True)
    image = fields.Binary(string='Badge Image', attachment=True)
    rule_type = fields.Selection([
        ('auto', 'Automatic'),
        ('manual', 'Manual Award')
    ], string='Award Rule', default='auto')
    rule_attendance = fields.Float(string='Min Attendance %', default=100.0)
    rule_assignments = fields.Float(string='Min Assignment Score %', default=90.0)
    rule_participations = fields.Integer(string='Min Participations', default=5)
    active = fields.Boolean(default=True)

    def _cron_award_badges(self):
        """Cron job to automatically award badges based on rules"""
        for badge in self.search([('rule_type', '=', 'auto')]):
            badge._award_automatic_badges()

    def _award_automatic_badges(self):
        """Award badges based on automatic rules"""
        if self.badge_type == 'attendance':
            self._award_attendance_badges()
        elif self.badge_type == 'assignment':
            self._award_assignment_badges()
        elif self.badge_type == 'participation':
            self._award_participation_badges()

    def _award_attendance_badges(self):
        """Award badges for perfect attendance"""
        Participant = self.env['ojt.participant']
        participants = Participant.search([
            ('state', '=', 'active'),
            ('attendance_rate', '>=', self.rule_attendance)
        ])
        self._create_awards(participants)

    def _award_assignment_badges(self):
        """Award badges for assignment excellence"""
        Participant = self.env['ojt.participant']
        participants = Participant.search([
            ('state', '=', 'active'),
            ('score_avg', '>=', self.rule_assignments)
        ])
        self._create_awards(participants)

    def _create_awards(self, participants):
        """Create badge awards for participants"""
        Award = self.env['ojt.badge.award']
        for participant in participants:
            if not Award.search_count([
                ('badge_id', '=', self.id),
                ('participant_id', '=', participant.id)
            ]):
                Award.create({
                    'badge_id': self.id,
                    'participant_id': participant.id,
                    'awarded_date': fields.Date.today()
                })

class OjtBadgeAward(models.Model):
    _name = 'ojt.badge.award'
    _description = 'OJT Badge Awards'
    _order = 'awarded_date desc, id desc'

    badge_id = fields.Many2one('ojt.gamification', string='Badge', required=True)
    participant_id = fields.Many2one('ojt.participant', string='Participant', required=True)
    awarded_date = fields.Date(string='Awarded Date', default=fields.Date.today)
    points = fields.Integer(related='badge_id.points', store=True)
    awarded_by = fields.Many2one('res.users', string='Awarded By', default=lambda self: self.env.user)
    notes = fields.Text(string='Award Notes')

class OjtParticipant(models.Model):
    _inherit = 'ojt.participant'

    badge_ids = fields.One2many('ojt.badge.award', 'participant_id', string='Badges')
    total_points = fields.Integer(compute='_compute_total_points', store=True, string='Total Points')
    rank = fields.Integer(compute='_compute_rank', string='Rank')
    
    @api.depends('badge_ids.points')
    def _compute_total_points(self):
        for record in self:
            record.total_points = sum(record.badge_ids.mapped('points'))

    def _compute_rank(self):
        """Compute participant rank based on total points"""
        participants = self.search([('batch_id', '=', self.batch_id.id)])
        sorted_participants = participants.sorted(key=lambda r: r.total_points, reverse=True)
        for idx, participant in enumerate(sorted_participants, 1):
            participant.rank = idx