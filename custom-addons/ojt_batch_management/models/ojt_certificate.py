from odoo import models, fields, api, _
from odoo.exceptions import UserError



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
        """Generate automatic certificate number"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('ojt.certificate') or 'New'
        return super().create(vals)

    # ----------------------------------------------------------
    # PDF GENERATION
    # ----------------------------------------------------------
    def generate_pdf(self):
        """Generate certificate PDF and attach it to the record"""
        self.ensure_one()

        # Try multiple possible report references
        report = None
        possible_refs = [
            'ojt_batch_management.action_report_certificate',
            'ojt_batch_management.report_certificate',
            'ojt_batch_management.report_ojt_certificate',
        ]

        for ref in possible_refs:
            report = self.env.ref(ref, raise_if_not_found=False)
            if report:
                break

        # Fallback search by model
        if not report:
            report = self.env['ir.actions.report'].search([
                ('model', '=', 'ojt.certificate'),
                ('report_type', '=', 'qweb-pdf')
            ], limit=1)

        if not report:
            raise UserError(
                "Certificate report not found.\n\n"
                "Please ensure a report for model 'ojt.certificate' exists in XML.\n"
                "Expected XML ID: 'ojt_batch_management.action_report_certificate'"
            )

        # Render QWeb report as PDF
        try:
            pdf_content, _ = report._render_qweb_pdf([self.id])
        except AttributeError:
            pdf_content = report.render_qweb_pdf([self.id])[0]

        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        filename = f"{self.name}.pdf"

        # Write PDF into record
        self.write({
            'pdf_file': pdf_base64,
            'pdf_filename': filename,
        })

        # Create attachment for tracking
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': pdf_base64,
            'res_model': 'ojt.certificate',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        return attachment

    # ----------------------------------------------------------
    # ACTION ISSUE
    # ----------------------------------------------------------
    def action_issue(self):
        """Generate certificate, attach PDF, and email it to participant"""
        self.ensure_one()

        if self.state == 'issued':
            return True

        self.write({
            'state': 'issued',
            'issue_date': date.today(),
        })

        # Generate and attach PDF
        try:
            attachment = self.generate_pdf()
        except Exception as e:
            raise UserError(
                "Failed to generate certificate PDF.\n\n"
                f"{str(e)}\n\n"
                "Please check that:\n"
                "1. Report XML ID exists (e.g. ojt_batch_management.action_report_certificate)\n"
                "2. Report template is valid (no XML errors)\n"
                "3. Report model is set to 'ojt.certificate'"
            )

        # Send email
        template = self.env.ref('ojt_batch_management.email_template_certificate', raise_if_not_found=False)
        if template:
            try:
                mail_values = template.generate_email(self.id)
                mail = self.env['mail.mail'].create(mail_values)

                if attachment:
                    mail.write({'attachment_ids': [(4, attachment.id)]})

                mail.send()
            except Exception as e:
                # Log but continue
                self.env['ir.logging'].sudo().create({
                    'name': 'ojt_batch_management',
                    'type': 'server',
                    'dbname': self.env.cr.dbname,
                    'level': 'ERROR',
                    'message': f'Failed to send certificate email for record {self.id}: {str(e)}',
                    'path': 'ojt_certificate.action_issue',
                    'line': '0',
                    'func': 'action_issue',
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Certificate Issued'),
                        'message': _('Certificate generated successfully, but email could not be sent.'),
                        'type': 'warning',
                        'sticky': False,
                    }
                }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Certificate Issued'),
                'message': _('Certificate has been successfully generated and issued.'),
                'type': 'success',
                'sticky': False,
            }
        }