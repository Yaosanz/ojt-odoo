from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # --------------------------------------------------------------------------
    # FIELDS
    # --------------------------------------------------------------------------
    ojt_batch_id = fields.Many2one(
        'ojt.batch',
        string='OJT Batch',
        domain="[('state', 'in', ['recruit', 'ongoing']), ('active', '=', True)]",
        help="Select the OJT batch for this application",
    )

    ojt_participant_id = fields.Many2one(
        'ojt.participant',
        string='OJT Participant',
        readonly=True,
        help="The participant record created from this application",
    )

    # Visibility controls (for Odoo 17)
    show_ojt_batch = fields.Boolean(
        compute="_compute_show_ojt_fields",
        store=False,
        help="Control visibility of OJT Batch field",
    )
    show_enroll_button = fields.Boolean(
        compute="_compute_show_ojt_fields",
        store=False,
        help="Control visibility of Enroll OJT button",
    )

    # --------------------------------------------------------------------------
    # COMPUTE METHODS
    # --------------------------------------------------------------------------
    @api.depends('stage_id', 'ojt_batch_id')
    def _compute_show_ojt_fields(self):
        """Control visibility for OJT fields."""
        for rec in self:
            stage_name = rec.stage_id.name or ''
            rec.show_ojt_batch = (stage_name == 'On The Job Training')
            rec.show_enroll_button = bool(rec.ojt_batch_id and stage_name != 'On The Job Training')

    # --------------------------------------------------------------------------
    # MAIN BUSINESS LOGIC
    # --------------------------------------------------------------------------
    def create_participant_from_applicant(self):
        """Create OJT participant and send OJT activation email."""
        self.ensure_one()

        if not self.ojt_batch_id:
            raise ValidationError(_("Please select an OJT batch before enrolling."))

        if self.ojt_participant_id:
            return self.ojt_participant_id

        # Create or get partner
        partner = self.partner_id
        if not partner:
            partner_vals = {
                'name': self.partner_name or self.name,
                'email': self.email_from,
                'phone': self.partner_phone,
            }
            if hasattr(self, 'student_id') and self.student_id:
                partner_vals['ref'] = self.student_id
            partner = self.env['res.partner'].create(partner_vals)

        # Create participant
        participant = self.env['ojt.participant'].create({
            'batch_id': self.ojt_batch_id.id,
            'partner_id': partner.id,
            'applicant_id': self.id,
            'state': 'active',
        })
        self.ojt_participant_id = participant.id

        # ✅ Automatically grant portal access and send activation email
        if participant.partner_id.email:
            try:
                # Check if portal user already exists
                existing_user = self.env['res.users'].sudo().search([
                    ('login', '=', participant.partner_id.email)
                ], limit=1)

                if existing_user:
                    # Use existing user and ensure portal access
                    participant.user_id = existing_user.id
                    group_portal = self.env.ref('base.group_portal')
                    if group_portal and group_portal.id not in existing_user.groups_id.ids:
                        existing_user.sudo().write({
                            'groups_id': [(4, group_portal.id)]
                        })
                    _logger.info("✅ Using existing portal user for %s", participant.partner_id.email)
                else:
                    # Create new portal user - allow same email but different login
                    group_portal = self.env.ref('base.group_portal')
                    if group_portal:
                        # Generate unique login based on participant name and batch
                        batch_name = participant.batch_id.name or 'OJT'
                        participant_name = participant.partner_id.name.replace(' ', '_').lower()
                        base_login = f"{participant_name}_{batch_name.lower().replace(' ', '_')}"

                        # Ensure login uniqueness
                        login = base_login
                        counter = 1
                        while self.env['res.users'].sudo().search_count([('login', '=', login)]) > 0:
                            login = f"{base_login}_{counter}"
                            counter += 1

                        user_vals = {
                            'name': participant.partner_id.name,
                            'login': login,
                            'email': participant.partner_id.email,
                            'partner_id': participant.partner_id.id,
                            'groups_id': [(6, 0, [group_portal.id])],
                        }
                        user = self.env['res.users'].sudo().create(user_vals)
                        participant.user_id = user.id
                        _logger.info("✅ Portal user created for %s with login %s", participant.partner_id.email, login)

                # Send OJT-specific activation email using custom template
                if participant.user_id:
                    # Use custom OJT activation email template instead of default signup
                    template = self.env.ref('ojt_batch_management.email_template_ojt_account_activation', raise_if_not_found=False)
                    if template:
                        # Send email immediately with force_send=True
                        mail_id = template.sudo().send_mail(participant.id, force_send=True, email_values={'email_to': participant.partner_id.email})
                        if mail_id:
                            _logger.info("✅ OJT activation email sent to %s (mail_id: %s)", participant.partner_id.email, mail_id)
                        else:
                            _logger.warning("⚠️ OJT activation email may not have been sent to %s", participant.partner_id.email)
                    else:
                        # Fallback to default signup email if template not found
                        participant.user_id.sudo().action_reset_password()
                        _logger.info("✅ Default signup email sent to %s (OJT template not found)", participant.partner_id.email)
                else:
                    _logger.error("❌ Failed to set up portal user for participant")

            except Exception as e:
                _logger.error("❌ Failed to grant portal access or send activation email: %s", e)

        return participant

    def action_enroll_ojt(self):
        """Action button to enroll applicant in OJT program and send activation email."""
        self.ensure_one()

        if not self.ojt_batch_id:
            raise ValidationError(_("Please select an OJT batch before enrolling."))

        # Move applicant to OJT stage if available (without triggering HR emails)
        ojt_stage = self.env.ref(
            'ojt_batch_management.hr_recruitment_stage_ojt', raise_if_not_found=False
        )
        if ojt_stage:
            # Use context to prevent HR recruitment emails during OJT enrollment
            self.with_context(skip_hr_recruitment_emails=True).write({'stage_id': ojt_stage.id})

        # Create participant + send activation email (this will send portal email)
        participant = self.with_context(skip_hr_recruitment_emails=True).create_participant_from_applicant()

        # ✅ Ensure portal access is granted immediately and send activation email
        if participant and participant.user_id:
            try:
                # Ensure user has portal group
                group_portal = self.env.ref('base.group_portal')
                if group_portal and group_portal.id not in participant.user_id.groups_id.ids:
                    participant.user_id.sudo().write({
                        'groups_id': [(4, group_portal.id)]
                    })
                    _logger.info("✅ Portal access granted to %s", participant.user_id.login)

                # Send OJT activation email using custom template
                template = self.env.ref('ojt_batch_management.email_template_ojt_account_activation', raise_if_not_found=False)
                if template:
                    # Send email immediately with force_send=True
                    mail_id = template.sudo().send_mail(participant.id, force_send=True, email_values={'email_to': participant.partner_id.email})
                    if mail_id:
                        _logger.info("✅ OJT activation email sent to %s (mail_id: %s)", participant.partner_id.email, mail_id)
                    else:
                        _logger.warning("⚠️ OJT activation email may not have been sent to %s", participant.partner_id.email)
                else:
                    _logger.error("❌ OJT activation email template not found")

            except Exception as e:
                _logger.error("❌ Failed to grant portal access or send email: %s", e)
        else:
            _logger.error("❌ Participant or user_id not found after enrollment")

        # ✅ Success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('OJT Enrollment'),
                'message': _('Applicant enrolled successfully and OJT activation email has been sent.'),
                'type': 'success',
                'sticky': False,
            },
        }

    # --------------------------------------------------------------------------
    # OVERRIDES
    # --------------------------------------------------------------------------
    @api.model
    def create(self, vals):
        """Auto-create participant if accepted and batch selected."""
        record = super().create(vals)
        if record.ojt_batch_id and record.application_status == 'accepted':
            record.create_participant_from_applicant()
        return record

    def write(self, vals):
        """Auto-create participant when status/stage changes."""
        # Check if we need to prevent HR recruitment emails
        skip_hr_emails = self.env.context.get('skip_hr_recruitment_emails', False)

        result = super().write(vals)
        for rec in self:
            if (
                vals.get('application_status') == 'accepted'
                or (
                    'stage_id' in vals
                    and self.env.ref(
                        'ojt_batch_management.hr_recruitment_stage_ojt',
                        raise_if_not_found=False
                    )
                    and vals['stage_id'] == self.env.ref(
                        'ojt_batch_management.hr_recruitment_stage_ojt'
                    ).id
                )
            ):
                if rec.ojt_batch_id and not rec.ojt_participant_id:
                    rec.create_participant_from_applicant()
        return result
