# OJT Recruitment Integration Tasks

## Overview
Integrate OJT module with built-in recruitment module in Odoo 18. Add "Enroll OJT" button, new "On The Job Training" stage, and automatic participant creation with activation email.

## Tasks

### 1. Create Recruitment Stage Data
- [x] Create `data/hr_recruitment_stage.xml` with "On The Job Training" stage
- [x] Ensure stage sequence and proper configuration

### 2. Create Account Activation Email Template
- [x] Create email template for account activation in `data/mail_template.xml`
- [x] Template should include login credentials and activation link

### 3. Add Enroll OJT Button to Applicant Form
- [x] Create `views/hr_applicant_views.xml` to inherit hr.applicant form
- [x] Add "Enroll OJT" action button in header
- [x] Button should be visible when applicant has OJT batch selected

### 4. Modify HR Applicant Model
- [x] Update `models/hr_applicant.py` to handle stage changes
- [x] Add method to enroll OJT when stage is set to "On The Job Training"
- [x] Trigger participant creation and email sending

### 5. Update Manifest
- [x] Add new data files to `__manifest__.py`
- [x] Ensure proper loading order

### 6. Testing
- [ ] Test stage transition triggers enrollment
- [ ] Verify participant creation
- [ ] Check email sending
- [ ] Validate portal user creation

## Dependencies
- hr_recruitment module
- portal module
- mail module

## Notes
- Use Odoo 18 API
- Ensure compatibility with PostgreSQL 16
- Follow existing code patterns in the module
