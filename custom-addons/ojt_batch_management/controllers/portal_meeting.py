# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class OJTPortalMeeting(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        """Add meeting attendance count to portal home"""
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1)
        
        if participant and 'meeting_count' in counters:
            # Count meetings for this participant
            meeting_count = request.env['ojt.meeting.attendance'].sudo().search_count([
                ('event_link_id.batch_id', '=', participant.batch_id.id),
                ('state', 'in', ['scheduled', 'ongoing', 'completed'])
            ])
            values['meeting_count'] = meeting_count
            
        return values
    
    @http.route(['/my/ojt/meeting', '/my/ojt/meeting/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_my_ojt_meeting_attendance(self, page=1, sortby=None, filterby=None, **kw):
        """Display meeting attendance records for logged in participant"""
        partner = request.env.user.partner_id
        
        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1)
        
        if not participant:
            return request.render('ojt_batch_management.portal_ojt_meeting_attendance', {
                'participant': False,
                'page_name': 'meeting_attendance',
            })
        
        # Domain untuk filter meeting berdasarkan batch participant
        domain = [
            ('event_link_id.batch_id', '=', participant.batch_id.id),
            ('state', 'in', ['scheduled', 'ongoing', 'completed'])
        ]
        
        # Sorting options
        searchbar_sortings = {
            'date': {'label': 'Date', 'order': 'start_time desc'},
            'name': {'label': 'Name', 'order': 'name'},
            'status': {'label': 'Status', 'order': 'state'},
        }
        
        # Filter options
        searchbar_filters = {
            'all': {'label': 'All', 'domain': []},
            'scheduled': {'label': 'Scheduled', 'domain': [('state', '=', 'scheduled')]},
            'ongoing': {'label': 'Ongoing', 'domain': [('state', '=', 'ongoing')]},
            'completed': {'label': 'Completed', 'domain': [('state', '=', 'completed')]},
        }
        
        # Default sort and filter
        if not sortby:
            sortby = 'date'
        if not filterby:
            filterby = 'all'
            
        order = searchbar_sortings[sortby]['order']
        domain += searchbar_filters[filterby]['domain']
        
        # Count meetings
        meeting_count = request.env['ojt.meeting.attendance'].sudo().search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/ojt/meeting",
            url_args={'sortby': sortby, 'filterby': filterby},
            total=meeting_count,
            page=page,
            step=10
        )
        
        # Get meetings
        meetings = request.env['ojt.meeting.attendance'].sudo().search(
            domain, 
            order=order, 
            limit=10, 
            offset=pager['offset']
        )
        
        # Untuk setiap meeting, cari attendee data untuk participant ini
        meeting_data = []
        for meeting in meetings:
            attendee = request.env['ojt.meeting.attendee'].sudo().search([
                ('meeting_id', '=', meeting.id),
                ('participant_id', '=', participant.id)
            ], limit=1)
            
            meeting_data.append({
                'meeting': meeting,
                'attendee': attendee,
            })
        
        # Statistics
        total_meetings = len(meetings)
        present_count = len([m for m in meeting_data if m['attendee'] and m['attendee'].attendance_status == 'present'])
        total_duration = sum([m['attendee'].duration if m['attendee'] else 0 for m in meeting_data])
        
        values = {
            'participant': participant,
            'meetings': meetings,
            'meeting_data': meeting_data,
            'page_name': 'meeting_attendance',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
            'default_url': '/my/ojt/meeting',
            # Statistics
            'total_meetings': total_meetings,
            'present_count': present_count,
            'total_duration': total_duration,
        }
        
        return request.render('ojt_batch_management.portal_ojt_meeting_attendance', values)
    
    @http.route(['/my/ojt/meeting/<int:meeting_id>'], 
                type='http', auth="user", website=True)
    def portal_my_ojt_meeting_detail(self, meeting_id, **kw):
        """Display meeting attendance detail"""
        partner = request.env.user.partner_id
        
        # Get participant
        participant = request.env['ojt.participant'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1)
        
        if not participant:
            return request.redirect('/my')
        
        # Get meeting
        meeting = request.env['ojt.meeting.attendance'].sudo().browse(meeting_id)
        
        # Check if meeting belongs to participant's batch
        if meeting.event_link_id.batch_id != participant.batch_id:
            return request.redirect('/my/ojt/meeting')
        
        # Get attendee data
        attendee = request.env['ojt.meeting.attendee'].sudo().search([
            ('meeting_id', '=', meeting.id),
            ('participant_id', '=', participant.id)
        ], limit=1)
        
        values = {
            'participant': participant,
            'meeting': meeting,
            'attendee': attendee,
            'page_name': 'meeting_detail',
        }
        
        return request.render('ojt_batch_management.portal_ojt_meeting_detail', values)