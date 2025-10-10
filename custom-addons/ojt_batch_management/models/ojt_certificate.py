# -*- coding: utf-8 -*-
import base64
from datetime import date
from odoo import models, fields, api, _

class OjtCertificate(models.Model):
    _name = "ojt.certificate"
    _description = "OJT Completion Certificate"
    _order = "issue_date desc"

    name = fields.Char(string="Certificate No.", required=True, copy=False, readonly=True, default="New")
    participant_id = fields.Many2one('ojt.participant', string="Participant", required=True, ondelete='cascade')
    batch_id = fields.Many2one('ojt.batch', string="Batch", related='participant_id.batch_id', store=True)
    issue_date = fields.Date(string="Issue Date", default=fields.Date.context_today)
    mentor_name = fields.Char(string="Mentor / Supervisor")
    remarks = fields.Text(string="Remarks / Notes")
    pdf_file = fields.Binary(string="Certificate File", readonly=True)
    pdf_filename = fields.Char(string="PDF Filename")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
    ], string="Status", default='draft')

    _sql_constraints = [
        ('unique_certificate_per_participant', 'unique(participant_id)',
         'Each participant can only have one certificate!')
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('ojt.certificate') or 'New'
        record = super(OjtCertificate, self).create(vals)
        return record

    def generate_pdf(self):
        """Generate PDF from QWeb report, store as attachment and in pdf_file field"""
        self.ensure_one()
        # render qweb pdf
        report = self.env.ref('ojt_batch_management.report_ojt_certificate', False)
        if not report:
            raise UserError(_("Certificate report not found."))
        pdf_content = report._render_qweb_pdf([self.id])[0]  # bytes
        datas = base64.b64encode(pdf_content).decode('utf-8')
        filename = f"{self.name}.pdf"
        # store in binary field
        self.write({
            'pdf_file': datas,
            'pdf_filename': filename,
        })
        # create attachment linked to record
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': datas,
            'res_model': 'ojt.certificate',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        return attachment

    def action_issue(self):
        """Issue certificate: generate PDF, attach, send email to participant"""
        self.ensure_one()
        if self.state == 'issued':
            return True
        # set state and issue date
        self.state = 'issued'
        self.issue_date = date.today()
        # generate pdf and attachment
        attachment = self.generate_pdf()
        # send mail using template
        template = self.env.ref('ojt_batch_management.email_template_certificate', False)
        if template:
            # prepare email values
            mail_values = template.generate_email(self.id)
            # create mail.mail
            mail = self.env['mail.mail'].create(mail_values)
            # attach generated attachment
            if attachment:
                mail.write({'attachment_ids': [(4, attachment.id)]})
            try:
                mail.send()
            except Exception:
                # if sending fails, just log the message and continue
                _logger = self.env['ir.logging']
                _logger.sudo().create({
                    'name': 'ojt_batch_management',
                    'type': 'server',
                    'dbname': self.env.cr.dbname,
                    'level': 'ERROR',
                    'message': 'Failed to send certificate email for %s' % (self.id),
                    'path': 'ojt_certificate.action_issue',
                    'line': '0',
                    'func': 'action_issue',
                })
        return True
