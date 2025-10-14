import json
from datetime import datetime
from odoo import http
from odoo.http import request

class ApiController(http.Controller):

    @http.route('/api/v1/docs', type='http', auth='public', methods=['GET'])
    def api_docs(self):
        """Return API documentation"""
        docs = {
            "title": "OJT Batch Management API v1",
            "version": "1.0.0",
            "description": "Public API for certificate verification and graduates list",
            "base_url": "/api/v1",
            "endpoints": {
                "certificate_verify": {
                    "url": "/api/v1/certificates/verify/{serial}",
                    "method": "GET",
                    "description": "Verify certificate authenticity by serial number",
                    "parameters": {
                        "serial": "Certificate serial number (path parameter)"
                    },
                    "response": {
                        "success": "boolean",
                        "data": "Certificate details if valid",
                        "message": "Response message",
                        "timestamp": "ISO timestamp"
                    }
                },
                "graduates_list": {
                    "url": "/api/v1/certificates/graduates",
                    "method": "GET",
                    "description": "Get list of graduates with optional filtering",
                    "parameters": {
                        "batch_id": "Filter by batch ID (optional)",
                        "start_date": "Filter by issue date from (YYYY-MM-DD, optional)",
                        "end_date": "Filter by issue date to (YYYY-MM-DD, optional)",
                        "grade": "Filter by grade (A, B, C, D, F, optional)",
                        "limit": "Maximum records (default: 50, max: 500, optional)",
                        "offset": "Pagination offset (default: 0, optional)"
                    },
                    "response": {
                        "success": "boolean",
                        "data": {
                            "graduates": "List of graduate records",
                            "pagination": "Pagination info",
                            "filters": "Applied filters"
                        },
                        "message": "Response message",
                        "timestamp": "ISO timestamp"
                    }
                }
            },
            "examples": {
                "verify_certificate": "/api/v1/certificates/verify/ABC123",
                "graduates_list": "/api/v1/certificates/graduates?batch_id=1&grade=A&limit=10",
                "graduates_filtered": "/api/v1/certificates/graduates?start_date=2024-01-01&end_date=2024-12-31"
            }
        }
        return request.make_response(
            json.dumps(docs, indent=2),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/api/v1/certificates/verify/<string:serial>', type='http', auth='public', methods=['GET'])
    def verify_certificate(self, serial):
        """Verify certificate by serial number"""
        try:
            certificate = request.env['ojt.certificate'].sudo().search([
                ('name', '=', serial),
                ('state', '=', 'issued')
            ], limit=1)
            
            if certificate:
                data = {
                    'certificate_id': certificate.name,
                    'participant_name': certificate.participant_id.name,
                    'batch_name': certificate.batch_id.name,
                    'issue_date': certificate.issue_date.strftime('%Y-%m-%d') if certificate.issue_date else None,
                    'final_score': certificate.final_score,
                    'grade': certificate.grade,
                    'mentor_name': certificate.mentor_name,
                    'remarks': certificate.remarks
                }
                return self._json_response(True, data, f"Certificate {serial} is valid")
            else:
                return self._json_response(False, None, "Certificate not found or invalid")
                
        except Exception as e:
            return self._json_response(False, None, f"Error verifying certificate: {str(e)}")

    @http.route('/api/v1/certificates/graduates', type='http', auth='public', methods=['GET'])
    def get_graduates(self, **kwargs):
        """Get list of graduates with filtering and pagination"""
        try:
            # Parse parameters
            batch_id = kwargs.get('batch_id')
            start_date = kwargs.get('start_date')
            end_date = kwargs.get('end_date')
            grade = kwargs.get('grade')
            limit = min(int(kwargs.get('limit', 50)), 500)  # Max 500
            offset = max(int(kwargs.get('offset', 0)), 0)   # Min 0
            
            # Build domain
            domain = [('state', '=', 'issued')]
            
            if batch_id:
                domain.append(('batch_id', '=', int(batch_id)))
            if start_date:
                domain.append(('issue_date', '>=', start_date))
            if end_date:
                domain.append(('issue_date', '<=', end_date))
            if grade:
                domain.append(('grade', '=', grade))
            
            # Get total count
            total_count = request.env['ojt.certificate'].sudo().search_count(domain)
            
            # Get records with pagination
            certificates = request.env['ojt.certificate'].sudo().search(
                domain, limit=limit, offset=offset, order='issue_date desc'
            )
            
            # Format response
            graduates = []
            for cert in certificates:
                graduates.append({
                    'certificate_id': cert.name,
                    'participant_name': cert.participant_id.name,
                    'batch_name': cert.batch_id.name,
                    'issue_date': cert.issue_date.strftime('%Y-%m-%d') if cert.issue_date else None,
                    'final_score': cert.final_score,
                    'grade': cert.grade,
                    'mentor_name': cert.mentor_name
                })
            
            data = {
                'graduates': graduates,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + limit) < total_count
                },
                'filters': {
                    'batch_id': batch_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'grade': grade
                }
            }
            
            message = f"Found {len(graduates)} graduates"
            if total_count > len(graduates):
                message += f" (showing {offset + 1}-{offset + len(graduates)} of {total_count})"
            
            return self._json_response(True, data, message)
            
        except Exception as e:
            return self._json_response(False, None, f"Error retrieving graduates: {str(e)}")

    def _json_response(self, success, data, message):
        """Helper method to create consistent JSON responses"""
        response = {
            'success': success,
            'data': data,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        return request.make_response(
            json.dumps(response, indent=2),
            headers=[('Content-Type', 'application/json')]
        )
