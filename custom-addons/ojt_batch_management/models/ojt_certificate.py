import uuid
import base64
import io
import logging
import qrcode
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class OjtCertificate(models.Model):
    _name = "ojt.certificate"
    _description = "OJT Completion Certificate"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "issue_date desc"

    # ----------------------------------------------------------
    # FIELDS
    # ----------------------------------------------------------
    name = fields.Char(
        string="Certificate No.",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )
    participant_id = fields.Many2one(
        "ojt.participant",
        string="Participant",
        required=True,
        ondelete="cascade",
    )
    batch_id = fields.Many2one(
        "ojt.batch", string="Batch", related="participant_id.batch_id", store=True
    )
    issue_date = fields.Date(string="Issue Date", default=fields.Date.context_today)
    issued_on = fields.Date(string="Issued On", readonly=True)
    mentor_name = fields.Char(string="Mentor / Supervisor")
    remarks = fields.Text(string="Remarks / Notes")

    pdf_file = fields.Binary(string="Certificate File", readonly=True)
    pdf_filename = fields.Char(string="PDF Filename")

    state = fields.Selection(
        [("draft", "Draft"), ("issued", "Issued")], string="Status", default="draft"
    )

    serial = fields.Char(string="Serial Number", readonly=True)

    attendance_rate = fields.Float(
        string="Attendance Rate",
        compute="_compute_participant_values",
        store=False,
        readonly=True,
    )
    final_score = fields.Float(
        string="Final Score",
        compute="_compute_participant_values",
        store=False,
        readonly=True,
    )
    grade = fields.Char(
        string="Grade", compute="_compute_participant_values", store=False, readonly=True
    )

    qr_code_image = fields.Binary(string="QR Code", compute="_compute_qr_code", store=True)

    _sql_constraints = [
        (
            "unique_certificate_per_participant",
            "unique(participant_id)",
            "Each participant can only have one certificate!",
        )
    ]

    # ----------------------------------------------------------
    # CREATE METHOD
    # ----------------------------------------------------------
    @api.model
    def create(self, vals):
        """Generate automatic certificate number"""
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code("ojt.certificate") or "New"
        return super().create(vals)

    # ----------------------------------------------------------
    # PDF GENERATION
    # ----------------------------------------------------------
    def _find_certificate_report_action(self):
        """
        Robust lookup for the report action to generate certificate PDF.
        Tries a few common xmlids / names, then falls back to searching
        by model + pdf/qweb type.
        Returns an ir.actions.report record or None.
        """
        # try common xmlids (adjust these strings to your module's xmlids if different)
        candidates = [
            "ojt_batch_management.action_report_certificate",
            "ojt_batch_management.report_certificate",
            "ojt_batch_management.report_certificate_action",
            "ojt_batch_management.report_certificate_template",
        ]
        for xmlid in candidates:
            try:
                report = self.env.ref(xmlid, raise_if_not_found=False)
                if report and report.exists():
                    return report
            except Exception:
                # ignore and continue to next candidate
                continue

        # fallback: search by model and report_type (qweb-pdf)
        report = (
            self.env["ir.actions.report"]
            .search(
                [
                    ("model", "=", "ojt.certificate"),
                    ("report_type", "in", ["qweb-pdf", "qweb-html", "qweb"]),
                ]
            )
            .sorted(key=lambda r: r.id)
        )
        return report[:1] or None

    def generate_pdf(self):
        """Generate certificate PDF and attach it to the record"""
        self.ensure_one()

        report = self._find_certificate_report_action()
        if not report:
            raise UserError(
                _(
                    "Certificate report action not found.\n\n"
                    "Please ensure the report action and template exist and are properly configured.\n"
                    "Expected report xmlid (examples): 'ojt_batch_management.action_report_certificate' or similar."
                )
            )

        # Prepare data for report rendering
        data = {
            "model": "ojt.certificate",
            "ids": [self.id],
            "form": self.read()[0] if self.exists() else {},
        }

        # Try to render PDF
        try:
            # Some Odoo versions expect report._render_qweb_pdf, others provide render_qweb_pdf
            # We try to be compatible:
            if hasattr(report, "_render_qweb_pdf"):
                pdf_content, content_type = report.with_context(active_model="ojt.certificate")._render_qweb_pdf(self.ids, data=data)
            elif hasattr(report, "render_qweb_pdf"):
                pdf_content, content_type = report.with_context(active_model="ojt.certificate").render_qweb_pdf(self.ids)
            else:
                # final fallback: use env['ir.actions.report'] helper
                pdf_content, content_type = self.env["ir.actions.report"]._render_qweb_pdf(report.id, self.ids, data=data)
        except Exception as e:
            # log full exception for debugging
            _logger.exception("Failed to render certificate PDF for record %s: %s", self.id, e)
            raise UserError(
                _(
                    "Failed to generate certificate PDF.\n\n"
                    "Error: %s\n\n"
                    "Please verify that:\n"
                    "1. The report template exists and is valid\n"
                    "2. All required fields are properly set\n"
                    "3. The report model matches the certificate model"
                )
                % str(e)
            )

        if not pdf_content:
            raise UserError(_("Report rendered no content; PDF generation failed."))

        # Ensure bytes
        if isinstance(pdf_content, str):
            pdf_bytes = pdf_content.encode("utf-8")
        else:
            pdf_bytes = pdf_content

        # Encode PDF content (store as base64 string for binary field)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # sanitize filename
        raw_name = self.pdf_filename or f"Certificate_{self.name}"
        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in raw_name)
        filename = safe_name if safe_name.lower().endswith(".pdf") else f"{safe_name}.pdf"

        # Write PDF into record (suppress recompute chatter spam)
        self.sudo().write({"pdf_file": pdf_base64, "pdf_filename": filename})

        # Create attachment for tracking / email (use sudo to ensure creation)
        try:
            attachment = self.env["ir.attachment"].sudo().create(
                {
                    "name": filename,
                    "type": "binary",
                    "datas": pdf_base64,
                    "res_model": "ojt.certificate",
                    "res_id": self.id,
                    "mimetype": "application/pdf",
                }
            )
        except Exception as e:
            _logger.exception("Failed to create attachment for certificate %s: %s", self.id, e)
            # still return success of PDF generation, just None attachment
            attachment = None

        return attachment

    # ----------------------------------------------------------
    # ISSUE ACTION
    # ----------------------------------------------------------
    def action_issue(self):
        """Generate certificate, attach PDF, and email it to participant"""
        self.ensure_one()

        if self.state == "issued":
            return True

        self.write(
            {
                "state": "issued",
                "issued_on": date.today(),
                "serial": str(uuid.uuid4()),
            }
        )
        # update computed stored-related fields from participant (not stored but helpful)
        # (if participant fields exist)
        try:
            self.sudo().write(
                {
                    "attendance_rate": self.participant_id.attendance_rate or 0.0,
                    "final_score": self.participant_id.score_final or 0.0,
                    "grade": self._compute_grade(self.participant_id.score_final),
                }
            )
        except Exception:
            # ignore write failure to computed or readonly fields
            pass

        # Generate and attach PDF
        try:
            attachment = self.generate_pdf()
        except Exception as e:
            _logger.exception("Failed to generate certificate PDF for record %s: %s", self.id, e)
            raise UserError(
                _(
                    "Failed to generate certificate PDF.\n\n%s\n\nPlease check that:\n"
                    "1. Report XML ID exists (e.g. ojt_batch_management.action_report_certificate)\n"
                    "2. Report template is valid (no XML errors)\n"
                    "3. Report model is set to 'ojt.certificate'"
                )
                % str(e)
            )

        # Send email if template exists
        template = self.env.ref("ojt_batch_management.email_template_certificate", raise_if_not_found=False)
        if template:
            try:
                mail_values = template.generate_email(self.id)
                mail = self.env["mail.mail"].create(mail_values)
                if attachment:
                    mail.write({"attachment_ids": [(4, attachment.id)]})
                mail.send()
            except Exception as e:
                # do not try to create ir.logging record from portal users
                _logger.exception("Failed to send certificate email for record %s: %s", self.id, e)
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Certificate Issued"),
                        "message": _("Certificate generated successfully, but email could not be sent."),
                        "type": "warning",
                        "sticky": False,
                    },
                }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Certificate Issued"),
                "message": _("Certificate has been successfully generated and issued."),
                "type": "success",
                "sticky": False,
            },
        }

    # ----------------------------------------------------------
    # GRADE COMPUTATION
    # ----------------------------------------------------------
    def _compute_grade(self, score):
        """Compute grade based on final score"""
        try:
            if score is None:
                return "F"
            # ensure float comparison
            sc = float(score)
        except Exception:
            return "F"

        if sc >= 90:
            return "A"
        elif sc >= 80:
            return "B"
        elif sc >= 70:
            return "C"
        elif sc >= 60:
            return "D"
        return "F"

    @api.depends("participant_id.attendance_rate", "participant_id.score_final")
    def _compute_participant_values(self):
        for record in self:
            record.attendance_rate = record.participant_id.attendance_rate or 0.0
            record.final_score = record.participant_id.score_final or 0.0
            record.grade = record._compute_grade(record.final_score)

    # ----------------------------------------------------------
    # QR CODE COMPUTATION
    # ----------------------------------------------------------
    @api.depends("serial")
    def _compute_qr_code(self):
        """Generate QR code image for certificate verification"""
        for record in self:
            if record.serial:
                # Generate QR code containing verification URL
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                # use absolute or relative verification URL as you prefer
                verification_url = f"/ojt/cert/verify?serial={record.serial}"
                qr.add_data(verification_url)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                record.qr_code_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
            else:
                record.qr_code_image = False

    # ----------------------------------------------------------
    # CERTIFICATE VERIFICATION
    # ----------------------------------------------------------
    @api.model
    def verify_certificate(self, serial):
        """Verify certificate authenticity using serial number"""
        certificate = self.search([("serial", "=", serial)], limit=1)
        if certificate and certificate.state == "issued":
            return {
                "valid": True,
                "certificate_no": certificate.name,
                "participant_name": certificate.participant_id.name,
                "batch": certificate.batch_id.name,
                "issue_date": certificate.issued_on or certificate.issue_date,
                "grade": certificate.grade,
                "serial": certificate.serial,
            }
        return {"valid": False, "reason": _("Certificate not found or not issued.")}
