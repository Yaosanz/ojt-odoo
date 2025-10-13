from odoo import http
from odoo.http import request

class OJTBatchPortal(http.Controller):

    @http.route(['/my/ojt'], type='http', auth='user', website=True)
    def portal_ojt_dashboard(self, **kw):
        participant = request.env['ojt.participant'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        certificates = request.env['ojt.certificate'].sudo().search([('participant_id.user_id', '=', request.env.user.id)])
        assignments = request.env['ojt.assignment.submit'].sudo().search([('participant_id.user_id', '=', request.env.user.id)])
        progress_records = request.env['ojt.progress'].sudo().search([('participant_id.user_id', '=', request.env.user.id)])
        return request.render('ojt_batch_management.portal_ojt_dashboard', {
            'participant': participant,
            'certificates': certificates,
            'assignments': assignments,
            'progress_records': progress_records,
        })
