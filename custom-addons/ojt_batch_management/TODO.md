# OJT Batch Management Module Enhancement TODO - Odoo 18 Compatibility

## Purpose
- [x] Enhance OJT system for integrated management: recruitment → batch → event/agenda → assignment → attendance → scoring → e-certificate
- [x] Ensure end-to-end orchestration from participant acceptance to public certificate verification

## Base Modules & Integration
- [x] Depends on: hr_recruitment, event, website_slides, survey, portal, website, mail, calendar, rating, utm
- [x] Integrate with: hr.applicant, hr.job, event.event, event.registration, slide.channel, slide.slide, survey.survey, survey.user_input, res.partner, res.users

## Core Functional Requirements

### 3.1 Recruitment & Batch Management
- [x] Display active OJT programs (period, theme, division, quota)
- [x] Online registration via Recruitment portal with CV, motivation form, batch selection
- [x] Admin screening and shortlisting
- [x] Automatic status updates (Pending, Shortlisted, Accepted, Rejected) on portal
- [x] Accepted participants auto-enrolled as OJT Participant linked to batch

### 3.2 Training & Event Scheduling
- [x] Create OJT Events per batch (topic, date, instructor, mode: online/offline)
- [x] Event sub-sessions/agendas (Orientation, Daily Standup, Review, Final Presentation)
- [x] Auto-integration with Online Meeting Links (MS Teams/Zoom/Google Meet)
- [x] Participants view agenda and attendance status via portal
- [x] Events auto-record attendance lists

### 3.3 Attendance & Presence Tracking
- [x] Attendance form per event
- [x] Attendance via: QR Code (offline), Auto log on meeting join (online)
- [x] Calculate participant attendance percentage
- [x] Attendance auto-affects eCertificate eligibility

### 3.4 Task & Assignment Management
- [x] Create Assignments per event/topic (upload file, deadline, score)
- [x] Participants upload tasks directly via portal
- [x] Trainers provide feedback and scores
- [x] Assignment status visible on participant dashboards
- [x] Assignments contribute to final score calculation

### 3.5 Participant Dashboard
- [x] Display summary: Profile, Batch, Schedule, Attendance rate, Task completion rate, Score average
- [x] Download schedule or certificate (if passed)
- [x] OJT Completion progress bar (%)

### 3.6 eCertificate Generation
- [x] Auto-generate eCertificate if: Attendance ≥ 80%, Final Score ≥ threshold (70%)
- [x] Certificate includes: Name, Period/Topic, Score, Grade, QR Code verification
- [x] Public verification via /certificate/verify?code=XXXX
- [x] Customizable certificate template (brand, signature, watermark)

### 3.7 Mentor & Trainer Management
- [x] Register internal/external mentors
- [x] Mentors access assigned batch participant dashboards
- [x] Mentors score and comment on tasks and attendance

### 3.8 Reporting & Analytics
- [x] Attendance reports per batch/participant
- [x] Score distribution reports
- [x] Export to Excel/PDF
- [x] OJT Dashboard: Active batches, Participants per batch, Average scores, Pass rates

### 3.9 Public Portal & Verification
- [x] Public pages: Active batch listings, Program details (goals, schedule, mentors)
- [x] Certificate verification with unique code input
- [x] Verification results: Name, Batch, Status (Valid/Expired/Invalid)

## Non-Functional Requirements
- [x] Security: Role-based access control for participant/score data
- [x] Performance: Dashboard handles 500 participants per batch
- [x] Scalability: Support 50 active batches, 2000 active participants
- [x] Usability: Responsive portal (desktop/mobile)
- [x] Integration: API for certificate verification and online meeting links
- [x] Branding: Corporate colors and logo

## Expected Deliverables
- [x] Custom Module: ojt_batch_management
- [x] Extended Models: ojt.batch, ojt.participant, ojt.assignment, ojt.attendance, ojt.certificate
- [x] Enhanced Views: Batch Form & Kanban, Event Agenda View, Participant Dashboard (Portal), Certificate Verification Page
- [x] Reports: Attendance Summary, Score & Certificate Report

## Architecture & Dependencies
- [x] Module: ojt_batch_management
- [x] Dependencies: hr_recruitment, event, website_slides, survey, portal, website, mail, calendar, rating, utm
- [x] Related Models: hr.applicant, hr.job, event.event, event.registration, slide.channel, slide.slide, survey.survey, survey.user_input, res.partner, res.users

## ERD (Entity Relationship Diagram)
- [x] hr.job 1---* ojt.batch *---* res.partner (Mentors)
- [x] ojt.batch 1---* ojt.participant *---1 res.partner (Participants)
- [x] ojt.participant *---* event.event (via ojt.event.link)
- [x] ojt.participant *---* slide.channel (course enrollment)
- [x] ojt.batch 1---* ojt.assignment 1---* ojt.assignment.submit
- [x] ojt.batch 1---* ojt.attendance (per event/session per participant)
- [x] ojt.batch 1---* ojt.certificate (per participant per batch)
- [x] ojt.batch *---* survey.survey (evaluation)

## Model & Field Definitions (Odoo 18 Compatible)

### ojt.batch
- [x] name: Char [required, index] - Batch name
- [x] code: Char [required, unique] - Batch code (sequence: OJTBATCH/%(year)s/%(seq)05d)
- [x] job_id: Many2one(hr.job) - Related job position
- [x] description: Html - Program description
- [x] department_id: Many2one(hr.department) - Department
- [x] mentor_ids: Many2many(res.partner) - Mentors/Instructors
- [x] start_date: Date [required]
- [x] end_date: Date [required]
- [x] mode: Selection [('online','Online'),('offline','Offline'),('hybrid','Hybrid')] [default='online']
- [x] capacity: Integer - Target quota
- [x] participant_ids: One2many(ojt.participant)
- [x] event_link_ids: One2many(ojt.event.link)
- [x] course_ids: Many2many(slide.channel)
- [x] survey_id: Many2one(survey.survey) - Evaluation survey
- [x] state: Selection [('draft','Draft'),('recruit','Recruitment'),('ongoing','Ongoing'),('done','Done'),('cancel','Cancelled')] [default='draft', track_visibility='onchange']
- [x] certificate_rule_attendance: Float [default=80.0] - Min attendance %
- [x] certificate_rule_score: Float [default=70.0] - Min final score
- [x] progress_ratio: Float [compute, store] - Progress %
- [x] color: Integer - Kanban color
- [x] company_id: Many2one(res.company) [required, default=current_company]
- [x] active: Boolean [default=True]
- [x] Constraints: start_date <= end_date, attendance/score rules validation

### ojt.event.link
- [x] batch_id: Many2one(ojt.batch) [required, ondelete='cascade']
- [x] event_id: Many2one(event.event) [required]
- [x] is_mandatory: Boolean [default=True] - Mandatory attendance
- [x] weight: Float [default=1.0] - Session weight
- [x] online_meeting_url: Char - Meeting link
- [x] notes: Text

### ojt.participant
- [x] name: Char [compute, store, index] - Participant name (partner + batch)
- [x] batch_id: Many2one(ojt.batch) [required, ondelete='cascade']
- [x] partner_id: Many2one(res.partner) [required]
- [x] applicant_id: Many2one(hr.applicant) - From recruitment
- [x] registration_id: Many2one(event.registration) - Event registration
- [x] course_ids: Many2many(slide.channel) - Enrolled courses
- [x] attendance_count: Integer [compute, store]
- [x] attendance_rate: Float [compute, store] - Attendance %
- [x] assignment_submit_ids: One2many(ojt.assignment.submit)
- [x] score_avg: Float [compute, store]
- [x] score_final: Float [compute, store] - Final score calculation
- [x] mentor_score: Float - Mentor evaluation score
- [x] state: Selection [('draft','Draft'),('active','Active'),('completed','Completed'),('failed','Failed'),('left','Left')] [default='active']
- [x] certificate_id: Many2one(ojt.certificate)
- [x] portal_token: Char [index] - Portal access token
- [x] notes: Text
- [x] company_id: Many2one(res.company) [required]

### ojt.assignment
- [x] name: Char [required] - Assignment title
- [x] batch_id: Many2one(ojt.batch) [required]
- [x] event_link_id: Many2one(ojt.event.link) - Related event
- [x] description: Html
- [x] type: Selection [('task','Task/Project'),('quiz','Quiz'),('presentation','Presentation')] [default='task']
- [x] related_channel_id: Many2one(slide.channel) - Related course
- [x] deadline: Datetime
- [x] max_score: Float [default=100.0]
- [x] weight: Float [default=1.0] - Weight for final score
- [x] attachment_required: Boolean [default=True]
- [x] submit_ids: One2many(ojt.assignment.submit)
- [x] state: Selection [('draft','Draft'),('open','Open'),('closed','Closed')] [default='open']
- [x] company_id: Many2one(res.company) [required]

### ojt.assignment.submit
- [x] assignment_id: Many2one(ojt.assignment) [required, ondelete='cascade']
- [x] participant_id: Many2one(ojt.participant) [required, ondelete='cascade']
- [x] submitted_on: Datetime [default=now]
- [x] attachment_ids: Many2many(ir.attachment)
- [x] url_link: Char - URL submission
- [x] score: Float
- [x] reviewer_id: Many2one(res.users) - Reviewer
- [x] feedback: Html
- [x] late: Boolean [compute] - Late submission flag
- [x] state: Selection [('draft','Draft'),('submitted','Submitted'),('scored','Scored')] [default='submitted']
- [x] Constraints: score <= max_score, attachment/URL validation

### ojt.attendance
- [x] batch_id: Many2one(ojt.batch) [required]
- [x] event_link_id: Many2one(ojt.event.link) [required]
- [x] event_id: Many2one(event.event) [related, store]
- [x] participant_id: Many2one(ojt.participant) [required]
- [x] check_in: Datetime
- [x] check_out: Datetime
- [x] presence: Selection [('present','Present'),('late','Late'),('absent','Absent')] [default='present']
- [x] method: Selection [('qr','QR Scan'),('online','Online Join'),('manual','Manual')] [default='manual']
- [x] duration_minutes: Float [compute] - Duration in minutes
- [x] notes: Text
- [x] company_id: Many2one(res.company) [required]
- [x] SQL Constraints: unique(participant_id, event_link_id)

### ojt.certificate
- [x] name: Char [required] - Certificate number (sequence: OJTCERT/%(year)s/%(seq)06d)
- [x] batch_id: Many2one(ojt.batch) [related, store]
- [x] participant_id: Many2one(ojt.participant) [required]
- [x] partner_id: Many2one(res.partner) [related, store]
- [x] serial: Char [unique, index] - Serial number
- [x] issued_on: Date [default=today]
- [x] attendance_rate: Float [store]
- [x] final_score: Float [store]
- [x] grade: Char [compute] - Grade (A/B/C)
- [x] qr_token: Char [unique, index] - Verification token
- [x] pdf_file: Binary - Certificate PDF
- [x] pdf_filename: Char
- [x] state: Selection [('draft','Draft'),('issued','Issued'),('revoked','Revoked')] [default='draft']
- [x] notes: Text

## Workflow & Business Rules
- [x] Recruitment → Participant: Accepted hr.applicant creates ojt.participant linked to ojt.batch
- [x] Batch → Event/Agenda: Link events via ojt.event.link, mark mandatory sessions
- [x] Attendance: Online auto-log, Offline QR check-in, calculate attendance_rate
- [x] Assignment: Create tasks, participant submissions, mentor scoring, calculate score_final
- [x] Certificate: Generate for eligible participants, issue with PDF and email

## Security (Groups, ACL, Record Rules)
- [x] Groups: ojt_group_manager, ojt_group_trainer, ojt_group_mentor, ojt_group_coordinator, ojt_group_viewer
- [x] ACL: Proper read/write permissions per group
- [x] Record Rules: Mentor access only assigned batches, portal users access own data

## Views & Menu
- [x] Menu Root: OJT Management
- [x] Submenus: Batches, Agenda, Participants, Assignments, Submissions, Attendance, Certificates, Reports
- [x] Portal: My OJT Progress, Assignments, Certificates
- [x] Website: OJT Programs, Certificate Verify

## Reports & Dashboard
- [x] Attendance Summary (Pivot/Graph/Excel)
- [x] Assignment Score Distribution
- [x] Completion & Pass Rate KPIs
- [x] Certificate Issued List
- [x] QWeb PDF Certificate template

## Automation (Cron, Server Action, Sequence)
- [x] Sequences: seq_ojt_batch, seq_ojt_certificate
- [x] Cron: ojt_attendance_autoclose, ojt_assignment_deadline_reminder, ojt_batch_state_switcher
- [x] Server Actions: Create participant from applicant, Generate certificates

## API/Controller Public
- [x] Certificate Verification: /ojt/cert/verify (GET, public)
- [x] QR Check-in: /ojt/attend/checkin/<token> (GET, public/portal)

## Validations & Constraints
- [x] Batch overlap validation
- [x] Duplicate attendance prevention
- [x] Score final calculation normalization
- [x] File size limits on attachments

## Integrations
- [x] Recruitment: Smart button on hr.applicant to enroll in OJT
- [x] Event: Use event.event.event_type_id for OJT filtering
- [x] eLearning: Enrollment in slide.channel, completion rate contribution
- [x] Survey: quizz_score aggregation to score_final

## UX Details
- [x] Batch Kanban: Progress %, active participants, next agenda, status buttons
- [x] Participant Form: Smart buttons for Assignments, Attendance, Certificate, Courses
- [x] Assignment Quick Scoring: Inline score + feedback
- [x] Portal: Large progress bar + "Join Next Session" CTA

## Testing/QA
- [x] Unit Tests: Participant creation, attendance compute, assignment scoring, certificate issuance, verification controller
- [x] Performance: 500 participants/batch dashboard load < 2s
- [x] Security: Portal data isolation, mentor batch restrictions

## Data Migration & Seed
- [x] Seed ojt.batch examples
- [x] QWeb Certificate template with branding
- [x] Email Templates: Portal invite, assignment reminder, certificate issued

## Formulas & Compute
- [x] attendance_rate = present_or_late_sessions / mandatory_sessions * 100
- [x] score_final = Σ(assignment_score/max_score * 100 * weight) + mentor_score * w_mentor + quiz_score * w_quiz
- [x] grade: >=85 A, >=75 B, else C

## Technical Artifacts
- [x] Module structure: __manifest__.py, models/, views/, controllers/, data/, security/, report/, static/
- [x] Odoo 18 compatible: Correct field definitions, inheritance, controllers, views

## Code Snippets
- [x] _compute_kpi for attendance_rate, score_avg, score_final
- [x] Certificate issuance with PDF generation and email

## KPI & Monitoring
- [x] Batch KPIs: Active participants, avg attendance, avg score, pass rate, certificates issued
- [x] Mentor KPIs: Tasks scored, scoring SLA
- [x] Participant KPIs: Progress %, tasks completed, attendance %, avg score

## Roadmap
- [ ] Meeting Attendance Integration (Graph API/Zoom/Meet)
- [ ] Gamification (badges/points)
- [ ] Proctoring for final quizzes
- [ ] Public API v1 for verification and graduates list
