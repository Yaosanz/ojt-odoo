from odoo import models, fields, api, _


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # Add OJT batch selection field
    ojt_batch_id = fields.Many2one(
        'ojt.batch',
        string='OJT Batch',
        domain="[('state', 'in', ['recruit', 'ongoing']), ('active', '=', True)]",
        help="Select the OJT batch for this application"
    )

    # Track if applicant has been converted to participant
    ojt_participant_id = fields.Many2one(
        'ojt.participant',
        string='OJT Participant',
        readonly=True,
        help="The participant record created from this application"
    )

    def create_participant_from_applicant(self):
        """Create OJT participant from accepted applicant"""
        self.ensure_one()

        if not self.ojt_batch_id:
            return False

        if self.ojt_participant_id:
            return self.ojt_participant_id

        # Create or get partner
        partner = self.partner_id
        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.partner_name,
                'email': self.email_from,
                'phone': self.partner_phone,
                'ref': getattr(self, 'student_id', False),  # If student_id field exists
            })

        # Create participant
        participant_vals = {
            'batch_id': self.ojt_batch_id.id,
            'partner_id': partner.id,
            'applicant_id': self.id,
            'state': 'active',
        }

        participant = self.env['ojt.participant'].create(participant_vals)

        # Update applicant
        self.write({
            'ojt_participant_id': participant.id,
        })

        return participant

    @api.model
    def create(self, vals):
        """Override create to handle OJT batch selection"""
        record = super().create(vals)

        # Auto-create participant if batch is selected and application is accepted
        if record.ojt_batch_id and record.application_status == 'accepted':
            record.create_participant_from_applicant()

        return record

    def write(self, vals):
        """Override write to handle status changes"""
        result = super().write(vals)

        # Check if status changed to accepted and has OJT batch
        if vals.get('application_status') == 'accepted':
            for record in self:
                if record.ojt_batch_id and not record.ojt_participant_id:
                    record.create_participant_from_applicant()

        return result
