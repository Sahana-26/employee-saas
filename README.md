# EmployeeHub SaaS

End-to-end employee management SaaS starter built with Django, Django REST Framework, PostgreSQL, JWT authentication, role-based access control, and React. This version is PostgreSQL-only: employee data, attendance, leaves, payroll records, audit logs, login access, and document binary data are stored through PostgreSQL-backed Django models.

## Current version highlights

- No subscription billing module
- No cloud document storage dependency
- No employee invite flow
- Admin/HR can create employee profiles directly
- Admin/HR can assign login password while creating an employee
- Admin/HR can reset employee passwords manually
- Admin/HR can enable or disable employee login access
- Frontend menus are hidden based on logged-in user role
- Backend querysets are tenant-aware and role-aware
- Employees can log in directly using the email and password created by HR/Admin
- Shift Management added for work timings, weekly offs, grace period, half-day hours, full-day hours, and overtime rules
- Holiday Calendar added for public, company, festival, and optional holidays
- Attendance now auto-calculates shift, holiday, weekly off, late minutes, worked duration, and overtime minutes
- Monthly Attendance Report added with employee-wise present, late, half-day, leave, absent, holiday, weekly-off, worked-hour, and overtime summary
- Leave Balance Auto-Deduction added when leave requests are approved
- Leave balance is reversed automatically if an approved leave is later rejected or cancelled
- Payroll module upgraded with salary components, employee salary component assignment, payroll runs, payslip generation, payslip line items, approval, and mark-paid workflow
- Expense reimbursement module added with receipt storage inside PostgreSQL, approval/rejection, and payment workflow
- Notifications and internal announcements added with PostgreSQL-backed read tracking
- Company Policy Management added with PostgreSQL-stored policy documents and acknowledgement tracking
- Asset Management and IT Inventory added with PostgreSQL-stored invoices, warranty files, handover documents, and photos
- Employee Exit / Offboarding workflow added for resignation, termination, clearance, final settlement, documents, and login deactivation
- Recruitment / Applicant Tracking System added for job openings, candidates, interviews, offers, and candidate-to-employee conversion
- Training / Learning Management System added for courses, materials, enrollments, assessments, progress, and certificates

## Included modules

- Multi-tenant organizations
- JWT login and refresh
- Role-based access: Owner, Admin, HR, Manager, Employee, Payroll, IT / Asset Manager, Viewer
- Direct employee account creation without invitation
- Employees
- Departments
- Attendance check-in and check-out with shift/holiday calculation
- Shift management
- Holiday calendar
- Employee shift assignments
- Leave types
- Leave balances
- Leave requests and approvals with automatic leave balance deduction
- Monthly attendance reports
- Leave balance reports
- Payroll records
- Payroll components and employee salary components
- Payroll runs and generated payslips
- Expense categories and reimbursement claims
- Notifications
- Internal announcements
- Company policies and acknowledgement tracking
- Performance review and appraisal management
- Asset management and IT inventory
- Employee exit and offboarding workflow
- Recruitment / Applicant Tracking System
- Training / Learning Management System
- Employee documents stored inside PostgreSQL
- Audit logs
- React admin dashboard
- Docker-based local setup

## Role access summary

| Role | Main access |
|---|---|
| Owner | Full workspace, HR, payroll, settings |
| Admin | Full workspace, HR, payroll, settings |
| HR | Employees, departments, attendance records, leaves, documents, recruitment, training, policies, performance |
| Manager | Team-level attendance, leave, recruitment interview visibility, and team training progress |
| Employee | Own attendance, leaves, profile, expenses, policies, training, and certificates |
| Payroll | Payroll components, salary assignments, payroll runs, payslips, payment status, final settlement payment support |
| IT / Asset Manager | Asset inventory, asset assignment, asset return, IT clearance support |
| Viewer | Read-only workspace access where allowed |

## Tech stack

Backend:
- Python 3.12+
- Django 6.x compatible structure
- Django REST Framework
- Simple JWT
- PostgreSQL
- django-cors-headers

Frontend:
- React
- Vite
- Axios
- React Router

## Local setup using Docker

```bash
cd employee_saas_product
cp backend/.env.example backend/.env
docker compose up --build
```

Backend:

```text
http://localhost:8000/api/
```

Frontend:

```text
http://localhost:5173/
```

## First-time backend setup without Docker

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Frontend setup without Docker

```bash
cd frontend
npm install
npm run dev
```

## API flow

1. Register organization owner

```http
POST /api/auth/register-organization/
```

```json
{
  "organization_name": "AGSRT",
  "first_name": "Sneha",
  "last_name": "Admin",
  "email": "admin@agsrt.com",
  "password": "StrongPass123"
}
```

2. Login

```http
POST /api/auth/token/
```

```json
{
  "email": "admin@agsrt.com",
  "password": "StrongPass123"
}
```

3. Use the access token

```http
Authorization: Bearer <access_token>
```

## Direct employee creation without invite

HR/Admin can create an employee and login account in one request:

```http
POST /api/employees/
```

```json
{
  "email": "employee@agsrt.com",
  "first_name": "Test",
  "last_name": "Employee",
  "password": "StrongPass123",
  "role": "EMPLOYEE",
  "employee_code": "EMP001",
  "designation": "GIS Analyst",
  "department": 1,
  "employment_type": "FULL_TIME",
  "status": "ACTIVE",
  "salary_basic": 30000
}
```

The employee can then log in directly from the frontend using the same email and password. No email invite or cloud service is required.

## Employee password and access endpoints

```text
POST /api/employees/{id}/set-password/
POST /api/employees/{id}/disable-login/
POST /api/employees/{id}/enable-login/
```

Password reset body:

```json
{
  "password": "NewStrongPass123"
}
```

## Main endpoints

```text
/api/auth/register-organization/
/api/auth/token/
/api/auth/token/refresh/
/api/auth/me/
/api/organizations/
/api/memberships/
/api/departments/
/api/employees/
/api/employees/{id}/set-password/
/api/employees/{id}/disable-login/
/api/employees/{id}/enable-login/
/api/attendance/
/api/attendance/check-in/
/api/attendance/check-out/
/api/attendance/my-shift/
/api/reports/monthly-attendance/?month=6&year=2026
/api/reports/leave-balances/?year=2026
/api/shifts/
/api/holidays/
/api/shift-assignments/
/api/leave-types/
/api/leave-balances/
/api/leave-requests/
/api/payroll-records/
/api/payroll-components/
/api/salary-components/
/api/payroll-runs/
/api/payroll-runs/{id}/generate/
/api/payroll-runs/{id}/approve/
/api/payroll-runs/{id}/mark-paid/
/api/payroll-runs/{id}/payslips/
/api/payslips/
/api/documents/
/api/documents/{id}/download/
/api/policies/
/api/policies/{id}/publish/
/api/policies/{id}/archive/
/api/policies/{id}/acknowledge/
/api/policies/{id}/download-document/
/api/policies/{id}/acknowledgements/
/api/policies/pending-acknowledgements/
/api/asset-categories/
/api/assets/
/api/assets/{id}/assign/
/api/assets/{id}/return/
/api/asset-documents/{id}/download/
/api/offboarding-cases/
/api/offboarding-cases/{id}/submit/
/api/offboarding-cases/{id}/approve/
/api/offboarding-cases/{id}/reject/
/api/offboarding-cases/{id}/cancel/
/api/offboarding-cases/{id}/complete/
/api/offboarding-cases/{id}/deactivate-login/
/api/offboarding-clearance/
/api/offboarding-clearance/{id}/clear/
/api/offboarding-clearance/{id}/waive/
/api/final-settlements/
/api/final-settlements/{id}/approve/
/api/final-settlements/{id}/mark-paid/
/api/offboarding-documents/
/api/offboarding-documents/{id}/download/
/api/job-openings/
/api/job-openings/{id}/publish/
/api/candidates/
/api/candidates/{id}/download-resume/
/api/interviews/
/api/offers/
/api/offers/{id}/convert-to-employee/
/api/training-courses/
/api/training-courses/{id}/publish/
/api/training-courses/{id}/archive/
/api/training-courses/{id}/self-enroll/
/api/training-materials/
/api/training-materials/{id}/download/
/api/training-enrollments/
/api/training-enrollments/{id}/start/
/api/training-enrollments/{id}/update-progress/
/api/training-enrollments/{id}/complete/
/api/training-enrollments/{id}/issue-certificate/
/api/training-assessments/
/api/training-assessments/{id}/publish/
/api/training-submissions/
/api/training-submissions/{id}/review/
/api/training-certificates/
/api/training-certificates/{id}/download/
/api/audit-logs/
```


## Company Policy Management

HR/Admin/Owner can create company policies with policy code, version, category, summary, full content, targeted audience roles, acknowledgement requirement, and optional policy document upload. Policy document files are stored directly in PostgreSQL using binary data fields.

Policy flow:

```text
1. HR/Admin creates a policy
2. HR/Admin optionally uploads policy document
3. HR/Admin publishes the policy
4. Targeted employees receive a notification
5. Employee opens Policies page
6. Employee downloads or reads the policy
7. Employee acknowledges the policy
8. HR/Admin checks acknowledgement count and user-wise acknowledgement records
```

Policy endpoints:

```text
/api/policies/
/api/policies/{id}/publish/
/api/policies/{id}/archive/
/api/policies/{id}/acknowledge/
/api/policies/{id}/download-document/
/api/policies/{id}/acknowledgements/
/api/policies/pending-acknowledgements/
```

Policy categories:

```text
HR, ATTENDANCE, LEAVE, PAYROLL, EXPENSE, IT, SECURITY, CONDUCT, OTHER
```

## Shift and holiday setup flow

After creating the organization and employees, HR/Admin should configure attendance rules in this order:

1. Create a default shift

```http
POST /api/shifts/
```

```json
{
  "name": "General Shift",
  "start_time": "09:00",
  "end_time": "18:00",
  "break_minutes": 60,
  "grace_minutes": 10,
  "half_day_hours": "4.00",
  "full_day_hours": "8.00",
  "overtime_after_minutes": 30,
  "weekly_off_days": "SUN",
  "is_default": true,
  "is_active": true
}
```

2. Add holidays

```http
POST /api/holidays/
```

```json
{
  "name": "Independence Day",
  "date": "2026-08-15",
  "holiday_type": "PUBLIC",
  "is_optional": false,
  "description": "National holiday"
}
```

3. Assign a shift to a specific employee when the employee does not follow the default shift

```http
POST /api/shift-assignments/
```

```json
{
  "employee": 1,
  "shift": 1,
  "start_date": "2026-06-20",
  "end_date": null,
  "is_active": true
}
```

4. Employee check-in/check-out automatically attaches today’s shift and holiday information

```text
POST /api/attendance/check-in/
POST /api/attendance/check-out/
GET  /api/attendance/my-shift/
/api/reports/monthly-attendance/?month=6&year=2026
/api/reports/leave-balances/?year=2026
```

Attendance records now include:

```text
shift, holiday, duration_minutes, late_minutes, overtime_minutes, is_holiday, is_weekly_off, status
```


## Monthly attendance reports

The Reports page and API summarize employee attendance for a selected month and year.

```http
GET /api/reports/monthly-attendance/?month=6&year=2026
```

The response includes employee-wise:

```text
expected_work_days, present_days, half_days, leave_days, absent_days, holiday_days, weekly_off_days, late_count, worked_minutes, late_minutes, overtime_minutes
```

The report uses configured shifts, holidays, weekly-off rules, attendance records, and approved leaves. Employees see their own report. Managers see their own and team reports. HR/Admin/Owner can see organization-wide reports.

## Leave balance auto-deduction

Approved leave requests now automatically update the matching leave balance for the employee, leave type, and year.

```http
PATCH /api/leave-requests/{id}/
```

```json
{
  "status": "APPROVED"
}
```

If the employee does not already have a balance row for that leave type and year, the backend creates one using the leave type's yearly allocation. If the remaining balance is insufficient, approval is blocked.

If an approved leave is changed to rejected or cancelled, the used balance is reversed automatically.

Leave balance report:

```http
GET /api/reports/leave-balances/?year=2026
```

## Payroll and payslip generation

The Payroll page now supports a full monthly payroll workflow without subscription billing or cloud storage. All payroll configuration, generated payslips, payslip lines, status updates, and payment metadata are stored in PostgreSQL.

### 1. Create payroll components

Use components for recurring earnings and deductions such as HRA, transport allowance, professional tax, provident fund, or other company-specific salary heads.

```http
POST /api/payroll-components/
```

```json
{
  "name": "HRA",
  "component_type": "EARNING",
  "calculation_type": "PERCENT_BASIC",
  "default_amount": "0.00",
  "default_percent": "40.00",
  "is_taxable": true,
  "is_active": true
}
```

Supported calculation types:

```text
FIXED
PERCENT_BASIC
PERCENT_GROSS
```

### 2. Assign salary components to employees

```http
POST /api/salary-components/
```

```json
{
  "employee": 1,
  "component": 1,
  "amount": "0.00",
  "percent": "40.00",
  "effective_from": "2026-06-01",
  "effective_to": null,
  "is_active": true
}
```

The employee's `salary_basic` field is used as the basic salary. Payroll components are added on top of that or deducted from the gross salary.

### 3. Create payroll run

```http
POST /api/payroll-runs/
```

```json
{
  "month": 6,
  "year": 2026,
  "notes": "June 2026 payroll"
}
```

### 4. Generate payslips

```http
POST /api/payroll-runs/{id}/generate/
```

The backend generates employee-wise payslips by combining:

```text
employee salary_basic
payroll components
employee-specific salary components
approved paid leaves
approved unpaid leaves
attendance absences
half-days
overtime minutes
loss-of-pay days
```

Generated payslips include basic salary, gross earnings, deductions, net pay, payable days, loss-of-pay days, overtime amount, and line items.

### 5. Approve and mark paid

```http
POST /api/payroll-runs/{id}/approve/
POST /api/payroll-runs/{id}/mark-paid/
```

Once a payroll run is approved, it cannot be regenerated. Only approved payroll runs can be marked as paid.

### 6. View payslips

```http
GET /api/payroll-runs/{id}/payslips/
GET /api/payslips/
```

Payroll roles can view all payslips. Employees can view their own payslips. Managers can view their own and team payslips.


## Employee Exit / Offboarding Workflow

The Offboarding page manages employee exit from request to final closure. It is PostgreSQL-only and keeps resignation documents, clearance records, final settlement records, and offboarding files inside the database-backed Django models.

Offboarding flow:

```text
1. HR/Admin creates an offboarding case or employee creates their own resignation case
2. Case is submitted for review
3. HR/Admin approves the case and confirms approved last working day
4. System creates default clearance tasks for manager, HR, finance, and IT when assets are assigned
5. Responsible users clear, waive, or reject clearance tasks
6. Once clearance is done, final settlement is prepared
7. HR/Payroll approves and marks final settlement as paid
8. HR/Admin completes offboarding
9. Employee status becomes EXITED
10. HR/Admin can deactivate employee login access
```

Offboarding endpoints:

```text
/api/offboarding-cases/
/api/offboarding-cases/{id}/submit/
/api/offboarding-cases/{id}/approve/
/api/offboarding-cases/{id}/reject/
/api/offboarding-cases/{id}/cancel/
/api/offboarding-cases/{id}/complete/
/api/offboarding-cases/{id}/deactivate-login/
/api/offboarding-clearance/
/api/offboarding-clearance/{id}/clear/
/api/offboarding-clearance/{id}/waive/
/api/offboarding-clearance/{id}/reject/
/api/final-settlements/
/api/final-settlements/{id}/approve/
/api/final-settlements/{id}/mark-paid/
/api/offboarding-documents/
/api/offboarding-documents/{id}/download/
```

Offboarding includes:

```text
resignation and termination cases
notice period tracking
requested and approved last working day
manager, HR, finance, and IT clearance tasks
asset return readiness tracking
final settlement calculation
settlement approval and payment reference
relieving, experience, resignation, settlement, and clearance documents
login deactivation after exit completion
notifications to HR, payroll, IT, manager, and employee
```

## PostgreSQL-only storage design

This version does not include subscription billing and does not depend on cloud document storage. Uploaded employee documents are saved in the `documents_employeedocument` table using a binary column, along with filename, content type, size, employee, organization, and uploader metadata.

For very large production files, PostgreSQL can still store the data, but configure database backups, retention, and size monitoring carefully.

## Recommended next modules

1. Recruitment / Applicant Tracking System
2. Training and Certification Management
3. Advanced HR letters and template generator
4. Automated tests for all APIs
5. Production deployment

## Production checklist

- Move secrets to environment variables or a managed secret store
- Use HTTPS only
- Configure PostgreSQL backups and retention
- Add server-side token blacklist and rotation
- Add password reset only if the product needs self-service reset
- Add audit trail for all write operations
- Add automated tests and CI/CD

## Dashboard Charts + HR Summary Analytics

This version adds a role-aware analytics dashboard for Owner, Admin, HR, Manager, Payroll, and Employee users.

### New dashboard endpoint

```http
GET /api/reports/dashboard-summary/?month=6&year=2026
```

The endpoint returns PostgreSQL-backed analytics for the selected month/year:

```text
employee counts
active employee counts
department count
today present / late / absent summary
pending leave requests
monthly present / leave / absent / late summaries
worked hours and overtime
payroll gross / deductions / net totals
payroll status
attendance mix chart data
daily attendance trend data
department-wise summary
leave status summary
payroll status summary
```

### Role-aware analytics scope

```text
Owner/Admin/HR: full organization dashboard
Manager: own profile + direct team dashboard
Employee: own attendance, leave, and payroll dashboard
Payroll: payroll-relevant dashboard based on accessible employee records
```

### Frontend dashboard added

The React dashboard now includes:

```text
summary cards
monthly filter
attendance mix bar chart
department headcount chart
leave status chart
payroll status chart
last 14 days attendance trend
department-wise analytics table
```

No external charting library is required. The charts are built with React and CSS, so the frontend remains lightweight.

## Recommended next modules

1. Employee self-service profile update
2. Expense reimbursement module
3. Notifications and approval alerts
4. Automated API tests
5. Production deployment

## Employee Self-Service Profile Update

This version adds employee self-service profile management while keeping all data inside PostgreSQL.

### Added backend app

```text
apps.selfservice
```

### Employee profile fields added

```text
personal_email
permanent_address
date_of_birth
gender
blood_group
marital_status
emergency_contact_name
emergency_contact_phone
emergency_contact_relation
bank_name
bank_account_number
bank_ifsc
bank_branch
tax_id
```

### Direct employee profile update

Employees can update basic fields directly:

```http
GET /api/profile/me/
PATCH /api/profile/me/
```

Directly editable fields:

```text
first_name
last_name
phone
personal_email
address
permanent_address
emergency_contact_name
emergency_contact_phone
emergency_contact_relation
```

### HR-reviewed profile change requests

Employees can submit verified change requests for sensitive information such as bank details, tax ID, date of birth, gender, blood group, and marital status.

```http
GET /api/profile-change-requests/
POST /api/profile-change-requests/
POST /api/profile-change-requests/{id}/approve/
POST /api/profile-change-requests/{id}/reject/
```

Example request:

```json
{
  "requested_data": {
    "bank_name": "HDFC Bank",
    "bank_account_number": "1234567890",
    "bank_ifsc": "HDFC0001234",
    "tax_id": "ABCDE1234F"
  },
  "reason": "Updating salary account details"
}
```

### Role behavior

```text
Employee: View own profile, update basic fields, submit change requests, view own requests
Manager: Same as employee for own profile
HR/Admin/Owner: View all profile change requests, approve/reject requests
```

### Frontend added

```text
My Profile page
Profile summary card
Editable profile form
Verified change request form
HR approval/rejection table
Profile completion percentage
```

### Testing flow

```text
1. Login as employee
2. Open My Profile
3. Update phone/address/emergency contact
4. Submit bank/tax/date-of-birth change request
5. Login as HR/Admin
6. Open My Profile
7. Approve or reject the submitted request
8. Login again as employee and verify updated sensitive fields
```

## Recommended next modules

1. Expense Reimbursement Module
2. Notification Center for approvals and HR actions
3. Company Policy and Announcements
4. Automated API tests
5. Production deployment

## Notifications + Internal Announcements Module

This version adds a PostgreSQL-backed notification and announcement system.

### Notification Center

Personal notifications are created for workflow events such as leave submission, leave approval/rejection, profile change review, expense approval/rejection/payment, and payroll generation/payment.

```http
GET  /api/notifications/
POST /api/notifications/{id}/mark-read/
POST /api/notifications/{id}/mark-unread/
POST /api/notifications/mark-all-read/
GET  /api/notifications/unread-count/
```

Notification fields include:

```text
title
message
notification_type
related_module
related_object_id
action_url
is_read
read_at
```

### Internal Announcements

HR/Admin/Owner can publish announcements for everyone or specific roles.

```http
GET  /api/announcements/
POST /api/announcements/
POST /api/announcements/{id}/mark-read/
POST /api/announcements/{id}/publish/
POST /api/announcements/{id}/archive/
```

Audience control:

```text
Empty audience_roles = visible to all roles
Selected audience_roles = visible only to selected roles
```

Supported roles:

```text
OWNER
ADMIN
HR
MANAGER
EMPLOYEE
PAYROLL
VIEWER
```

### Frontend added

```text
Notifications page
Announcements page
Unread notification count
Mark notification read/unread
Mark all notifications read
Create announcements
Publish/archive announcements
Role-targeted announcement audience
Announcement read tracking
```

### Test flow

```text
1. Login as HR/Admin
2. Create an announcement for all roles or selected roles
3. Login as employee and mark the announcement as read
4. Submit an expense or leave request as employee
5. Login as manager/HR and approve or reject it
6. Login again as employee and verify notification appears
7. Generate/approve/mark paid payroll and verify payslip notifications
```

## Recommended next modules

1. Company Policy Management
2. Automated API Tests
3. Production deployment with Gunicorn/Nginx
4. Backup and restore workflow for PostgreSQL

## Company Policy Management Module

This version includes PostgreSQL-backed company policy management.

### Backend endpoints

```http
GET  /api/policies/
POST /api/policies/
POST /api/policies/{id}/publish/
POST /api/policies/{id}/archive/
POST /api/policies/{id}/acknowledge/
GET  /api/policies/{id}/download-document/
GET  /api/policies/{id}/acknowledgements/
GET  /api/policies/pending-acknowledgements/
```

### Frontend added

```text
Policies page
Policy document upload stored in PostgreSQL
Policy publish/archive workflow
Employee acknowledgement tracking
Role-targeted policy audience
```

## Performance Review / Appraisal Management Module

This version adds an end-to-end performance review and appraisal workflow.

### Backend features

```text
Performance review cycles
Employee goals / KRAs
Goal submission and approval
Goal rejection with reason
Goal self-rating and self-comments
Manager goal rating and comments
Employee self-review
Manager review
HR calibration and finalization
Final rating and final score tracking
Role-based visibility for HR, Manager, and Employee
Notifications for cycle publishing, goal submission, approvals, review submission, and finalization
```

### Backend endpoints

```http
GET    /api/performance-cycles/
POST   /api/performance-cycles/
POST   /api/performance-cycles/{id}/publish/
POST   /api/performance-cycles/{id}/close/

GET    /api/performance-goals/
POST   /api/performance-goals/
POST   /api/performance-goals/{id}/submit/
POST   /api/performance-goals/{id}/approve/
POST   /api/performance-goals/{id}/reject/
POST   /api/performance-goals/{id}/self-review/
POST   /api/performance-goals/{id}/manager-review/

GET    /api/performance-reviews/
POST   /api/performance-reviews/
POST   /api/performance-reviews/{id}/submit-self-review/
POST   /api/performance-reviews/{id}/submit-manager-review/
POST   /api/performance-reviews/{id}/finalize/
```

### Performance workflow

```text
1. HR/Admin creates a performance cycle
2. HR/Admin publishes the cycle
3. Employee/Manager/HR creates employee goals or KRAs
4. Employee or manager submits goals
5. Manager/HR approves or rejects goals
6. Employee adds goal self-rating and submits self-review
7. Manager adds goal rating and submits manager review
8. HR/Admin calibrates and finalizes final rating and score
9. Employee receives notification after finalization
```

### Frontend added

```text
Performance page
Cycle creation and publish/close actions
Goal/KRA creation
Goal approval/rejection
Goal self-rating and manager rating
Review record creation
Self-review form
Manager review form
HR finalization form
```

## Recommended next modules

1. Asset Management and IT Inventory
2. Employee Exit / Offboarding Workflow
3. Automated API Tests
4. Production deployment with Gunicorn/Nginx
5. PostgreSQL backup and restore workflow

## Asset Management and IT Inventory Module

This version adds a PostgreSQL-only asset and IT inventory workflow.

### Backend features

```text
Asset categories
IT asset register
Asset assignment to employees
Asset return workflow
Asset status tracking: Available, Assigned, Maintenance, Damaged, Lost, Retired
Assignment history
Asset document upload stored directly in PostgreSQL
Asset document download API
Maintenance records
Warranty and vendor tracking
New IT / Asset Manager role
Role-based visibility for Owner, Admin, HR, IT, Manager, and Employee
Notifications when assets are assigned or returned
```

### Backend endpoints

```http
GET    /api/asset-categories/
POST   /api/asset-categories/

GET    /api/assets/
POST   /api/assets/
POST   /api/assets/{id}/assign/
POST   /api/assets/{id}/return/
POST   /api/assets/{id}/mark-available/
POST   /api/assets/{id}/mark-maintenance/
POST   /api/assets/{id}/mark-damaged/
POST   /api/assets/{id}/mark-lost/
POST   /api/assets/{id}/mark-retired/

GET    /api/asset-assignments/
POST   /api/asset-assignments/

GET    /api/asset-documents/
POST   /api/asset-documents/
GET    /api/asset-documents/{id}/download/

GET    /api/asset-maintenance/
POST   /api/asset-maintenance/
```

### Asset workflow

```text
1. HR/Admin/IT creates asset categories
2. HR/Admin/IT creates asset records such as laptop, desktop, phone, SIM, software license, or accessory
3. HR/Admin/IT assigns asset to an employee
4. Employee receives asset notification
5. HR/Admin/IT uploads invoice, warranty, handover, or photo documents
6. HR/Admin/IT tracks maintenance, damage, lost, retired, and available status
7. Asset return creates assignment history and makes the asset available again
8. Employee and manager can view assigned asset records based on role visibility
```

### Frontend added

```text
Assets page
Asset category creation
Asset register creation
Asset assignment form
Asset document upload and download
Maintenance record form
Asset status action buttons
Assignment history table
Employee self-view of assigned assets
```

## Recommended next modules

1. Recruitment / Applicant Tracking System
2. Training and Certification Management
3. Automated API Tests
4. Production deployment with Gunicorn/Nginx
5. PostgreSQL backup and restore workflow


## Employee Exit / Offboarding Workflow Module

This version adds a complete PostgreSQL-only employee exit workflow. HR/Admin can manage resignation, termination, notice period, last working day, clearance tasks, final settlement, exit documents, and login deactivation. Employees can create their own resignation case, managers can track team exits, and HR/Payroll/IT can complete their respective clearance and settlement actions.

### Backend endpoints

```http
GET    /api/offboarding-cases/
POST   /api/offboarding-cases/
POST   /api/offboarding-cases/{id}/submit/
POST   /api/offboarding-cases/{id}/approve/
POST   /api/offboarding-cases/{id}/reject/
POST   /api/offboarding-cases/{id}/cancel/
POST   /api/offboarding-cases/{id}/complete/
POST   /api/offboarding-cases/{id}/deactivate-login/

GET    /api/offboarding-clearance/
POST   /api/offboarding-clearance/
POST   /api/offboarding-clearance/{id}/clear/
POST   /api/offboarding-clearance/{id}/waive/
POST   /api/offboarding-clearance/{id}/reject/

GET    /api/final-settlements/
POST   /api/final-settlements/
POST   /api/final-settlements/{id}/approve/
POST   /api/final-settlements/{id}/mark-paid/

GET    /api/offboarding-documents/
POST   /api/offboarding-documents/
GET    /api/offboarding-documents/{id}/download/
```

### Frontend added

```text
Offboarding page
Offboarding case creation
Submit, approve, reject, cancel, complete, and deactivate-login actions
Clearance task table with clear, waive, and reject actions
Final settlement form and approval/payment workflow
Offboarding document upload and download
```

## Recommended next modules

1. Recruitment / Applicant Tracking System
2. Training and Certification Management
3. Automated API Tests
4. Production deployment with Gunicorn/Nginx
5. PostgreSQL backup and restore workflow

## Added Module: Recruitment / Applicant Tracking System

This version adds a PostgreSQL-backed Recruitment / ATS module for HR and hiring managers.

### Features

- Job opening management
- Job publish, hold, close, and cancel workflow
- Candidate database
- Resume upload stored directly in PostgreSQL
- Resume download API
- Candidate screening, shortlist, hold, and rejection workflow
- Interview scheduling
- Interview feedback, rating, result, cancellation, and no-show tracking
- Offer letter creation
- Offer document upload stored directly in PostgreSQL
- Offer send, accept, reject, and withdraw workflow
- Candidate-to-employee conversion after offer acceptance
- Direct employee login creation during conversion
- Department, designation, joining date, salary, and role assignment
- Role-based access for HR/Admin/Owner and hiring managers
- Notifications for job publishing, candidate additions, interviews, and accepted offers

### New Backend Endpoints

```text
/api/job-openings/
/api/job-openings/{id}/publish/
/api/job-openings/{id}/hold/
/api/job-openings/{id}/close/
/api/job-openings/{id}/cancel/

/api/candidates/
/api/candidates/{id}/screen/
/api/candidates/{id}/shortlist/
/api/candidates/{id}/hold/
/api/candidates/{id}/reject/
/api/candidates/{id}/download-resume/

/api/interviews/
/api/interviews/{id}/complete/
/api/interviews/{id}/cancel/

/api/offers/
/api/offers/{id}/send/
/api/offers/{id}/accept/
/api/offers/{id}/reject/
/api/offers/{id}/withdraw/
/api/offers/{id}/convert-to-employee/
/api/offers/{id}/download-document/
```

### Frontend Page

```text
Recruitment
```

### Recommended Test Flow

```text
1. Login as HR/Admin/Owner.
2. Create a job opening.
3. Publish the job opening.
4. Add a candidate and upload resume.
5. Move candidate to screening or shortlist.
6. Schedule interview.
7. Complete interview with rating and feedback.
8. Create offer with joining date, designation, CTC, and offer document.
9. Mark offer as sent.
10. Mark offer as accepted.
11. Convert offer to employee by entering employee code, password, and role.
12. Login with the new employee email and password.
```


## Training / Learning Management System

The Training page supports an internal LMS workflow while keeping all uploaded materials inside PostgreSQL. HR/Admin/Owner can create courses, upload materials, assign employees, create assessments, review submissions, and issue completion certificates. Employees can view assigned courses, self-enroll in published courses, update progress, submit assessments, and download certificates.

Training flow:

```text
1. HR/Admin creates a training course
2. HR/Admin uploads course material or adds an external learning URL
3. HR/Admin publishes the course
4. HR/Admin assigns employees or employees self-enroll in published courses
5. Employee starts the course and updates progress
6. Employee submits assessment answers
7. HR/Admin reviews assessment score and feedback
8. Completed training generates a certificate record
9. Employee downloads certificate
```

Training endpoints:

```text
/api/training-courses/
/api/training-courses/{id}/publish/
/api/training-courses/{id}/archive/
/api/training-courses/{id}/self-enroll/
/api/training-materials/
/api/training-materials/{id}/download/
/api/training-enrollments/
/api/training-enrollments/{id}/start/
/api/training-enrollments/{id}/update-progress/
/api/training-enrollments/{id}/complete/
/api/training-enrollments/{id}/cancel/
/api/training-enrollments/{id}/issue-certificate/
/api/training-assessments/
/api/training-assessments/{id}/publish/
/api/training-assessments/{id}/archive/
/api/training-submissions/
/api/training-submissions/{id}/review/
/api/training-certificates/
/api/training-certificates/{id}/download/
```

Training material storage:

```text
file_name
content_type
file_size
file_data stored as PostgreSQL binary data
```

Test flow:

```text
1. Login as HR/Admin
2. Open Training / LMS
3. Create a course
4. Upload material
5. Publish the course
6. Assign the course to an employee
7. Login as employee
8. Start course and update progress
9. Submit assessment answers as JSON
10. Login as HR/Admin and review submission
11. Complete course and issue/download certificate
```


## Helpdesk / Employee Support Tickets

The Helpdesk page adds an internal support workflow for HR, IT, admin, and employee service requests. All ticket attachments are stored directly in PostgreSQL using binary fields, keeping the product PostgreSQL-only with no cloud document dependency.

Helpdesk flow:

```text
1. HR/Admin/IT creates ticket categories such as HR Query, IT Support, Payroll Issue, Access Request, or Asset Issue
2. Employee creates a support ticket with priority, category, subject, and description
3. HR/Admin/IT assigns the ticket to a support user and optionally sets a due date
4. Support user moves the ticket to in progress
5. Support user can request more information by marking it as pending user
6. Employee and support users can add comments
7. Support users can upload/download attachments stored in PostgreSQL
8. Support user resolves the ticket with resolution notes
9. Employee or support user closes the ticket
10. Ticket can be reopened or cancelled when needed
```

Helpdesk endpoints:

```text
/api/ticket-categories/
/api/support-tickets/
/api/support-tickets/{id}/assign/
/api/support-tickets/{id}/start/
/api/support-tickets/{id}/pending-user/
/api/support-tickets/{id}/resolve/
/api/support-tickets/{id}/close/
/api/support-tickets/{id}/reopen/
/api/support-tickets/{id}/cancel/
/api/support-tickets/{id}/add-comment/
/api/ticket-comments/
/api/ticket-attachments/
/api/ticket-attachments/{id}/download/
```

Helpdesk attachment storage:

```text
file_name
content_type
file_size
file_data stored as PostgreSQL binary data
```

Role-based access:

```text
Employee: create and track own tickets
Manager: view own and team tickets
HR/Admin/Owner/IT: manage all tickets, categories, assignments, internal notes, and resolutions
```

Test flow:

```text
1. Login as HR/Admin/IT
2. Open Helpdesk
3. Create support categories
4. Login as employee
5. Create a support ticket
6. Upload a ticket attachment
7. Login as HR/Admin/IT
8. Assign the ticket and start work
9. Add comments or mark as pending user
10. Resolve the ticket with resolution notes
11. Login as employee and close or reopen the ticket
```

## Timesheet / Project Worklog Management

The Timesheets module adds project-based work tracking for employees, managers, HR, and admins. It supports internal projects, project membership, task assignment, daily worklog entries, approval workflow, billable/non-billable hours, and monthly timesheet summary reporting. Everything remains PostgreSQL-only.

Timesheet flow:

```text
1. HR/Admin/Manager creates a work project
2. HR/Admin/Manager assigns project members
3. HR/Admin/Manager creates project tasks and assigns them to employees
4. Employee logs daily work hours against a project and optional task
5. Employee submits the timesheet entry for approval
6. Project manager, reporting manager, HR, Admin, or Owner approves/rejects it
7. Approved hours are used in monthly summary reports
8. Billable and non-billable hours are separated for operations and client billing reference
```

Timesheet endpoints:

```text
/api/work-projects/
/api/work-projects/{id}/activate/
/api/work-projects/{id}/hold/
/api/work-projects/{id}/complete/

/api/project-memberships/
/api/project-memberships/{id}/release/
/api/project-memberships/{id}/reactivate/

/api/project-tasks/
/api/project-tasks/{id}/start/
/api/project-tasks/{id}/review/
/api/project-tasks/{id}/done/
/api/project-tasks/{id}/blocked/

/api/timesheet-entries/
/api/timesheet-entries/{id}/submit/
/api/timesheet-entries/{id}/approve/
/api/timesheet-entries/{id}/reject/
/api/timesheet-entries/{id}/reopen/

/api/timesheets/monthly-summary/?month=6&year=2026
```

Timesheet report includes:

```text
submitted hours
approved hours
billable hours
non-billable hours
draft count
submitted/pending count
approved count
rejected count
employee-wise monthly totals
```

Role-based access:

```text
Employee: view assigned projects/tasks and create/submit own timesheets
Manager: view own/team/project timesheets and approve/reject when responsible
HR/Admin/Owner: full project, task, membership, approval, and report access
```

Test flow:

```text
1. Login as HR/Admin/Manager
2. Open Timesheets
3. Create a work project
4. Add project members
5. Create and assign a task
6. Login as employee
7. Create a timesheet entry and submit it
8. Login as manager/HR/Admin
9. Approve or reject the submitted timesheet
10. Check Monthly Timesheet Summary
```

## HR Letters and Document Template Generator

The HR Letters module adds template-based document generation for employee letters while keeping storage PostgreSQL-only. HR/Admin/Owner can create reusable letter templates with variables, generate employee-specific letters, approve/reject, sign, issue, and download generated files. Employees can view and download their own approved/signed/issued letters.

Supported letter categories:

```text
Offer Letter
Appointment Letter
Confirmation Letter
Increment Letter
Salary Certificate
Experience Letter
Relieving Letter
Warning Letter
NOC
Other
```

Template variables use Django-style placeholders:

```text
{{ organization.name }}
{{ today }}
{{ employee.employee_code }}
{{ employee.full_name }}
{{ employee.email }}
{{ employee.department }}
{{ employee.designation }}
{{ employee.date_of_joining }}
{{ employee.salary_basic }}
{{ employee.manager_name }}
{{ custom.amount }}
{{ custom.effective_date }}
{{ custom.signatory_name }}
{{ custom.signatory_designation }}
```

HR Letter endpoints:

```text
/api/hr-letter-templates/
/api/hr-letter-templates/variables/
/api/hr-letter-templates/{id}/render-preview/
/api/hr-letter-templates/{id}/activate/
/api/hr-letter-templates/{id}/archive/

/api/generated-letters/
/api/generated-letters/{id}/generate/
/api/generated-letters/{id}/approve/
/api/generated-letters/{id}/reject/
/api/generated-letters/{id}/sign/
/api/generated-letters/{id}/issue/
/api/generated-letters/{id}/cancel/
/api/generated-letters/{id}/download/
/api/generated-letters/{id}/history/
```

Workflow:

```text
1. HR/Admin creates a letter template with variables.
2. HR/Admin selects employee and template.
3. HR/Admin enters custom variables as JSON.
4. System renders the final document and stores it in PostgreSQL.
5. HR/Admin approves or rejects the generated letter.
6. HR/Admin signs and issues the letter.
7. Employee downloads the issued letter from the HR Letters page.
```

Storage approach:

```text
Template content: PostgreSQL TextField
Generated rendered content: PostgreSQL TextField
Generated downloadable document: PostgreSQL BinaryField
Document format: HTML/text file stored in PostgreSQL
```

Note: PDF export is intentionally not added to keep the project dependency-light. A PDF layer can be added later using WeasyPrint, Playwright, or an external rendering service if required.

---

## Final Core Module Added: System Settings, Audit, Backup and Production Readiness

This version adds the final core administration layer required before moving the HRMS SaaS into production testing.

### Added Features

- Organization-level system settings
- HR, attendance, leave and payroll rule configuration
- Weekly-off configuration
- Employee self-service permission switches
- Upload/data retention settings
- PostgreSQL backup request tracking
- Backup command helper endpoint
- Backup status lifecycle: requested, running, completed, failed
- System health endpoint
- System overview endpoint with module-wise record counts
- Latest audit activity visibility in Settings page
- Production backup and restore shell scripts
- Expanded Settings frontend page for Owner/Admin users

### New Backend App

```text
apps.systemsettings
```

### New Backend Models

```text
OrganizationSetting
BackupLog
```

### New Backend Endpoints

```text
GET   /api/system/settings/
PATCH /api/system/settings/

GET   /api/system/health/
GET   /api/system/overview/

GET   /api/backup-logs/
POST  /api/backup-logs/
GET   /api/backup-logs/backup-command/
POST  /api/backup-logs/{id}/mark-running/
POST  /api/backup-logs/{id}/mark-completed/
POST  /api/backup-logs/{id}/mark-failed/
```

### Settings Available

```text
app name
country
timezone
date format
currency
fiscal year start month
leave year start month
standard working hours per day
attendance grace minutes
half-day threshold hours
overtime rate per hour
weekly off days
default notice period days
default probation days
payroll lock day
document max upload size
data retention days
support email
employee profile edit permission
employee self-attendance permission
employee expense submission permission
LMS self-enrollment permission
IP restriction flag
allowed IP ranges
metadata JSON
```

### Backup Scripts

Backup PostgreSQL:

```bash
./scripts/backup_postgres.sh
```

Backup with custom file name:

```bash
./scripts/backup_postgres.sh employeehub-20260620.dump
```

Restore PostgreSQL:

```bash
./scripts/restore_postgres.sh ./backups/employeehub-20260620.dump
```

### Test Flow

```text
1. Login as Owner/Admin.
2. Open Settings.
3. Update HR, attendance and payroll rules.
4. Save settings.
5. Check system health.
6. Check module-wise overview counts.
7. Create backup request.
8. Copy backup command or run ./scripts/backup_postgres.sh on the server.
9. Mark backup as running/completed/failed.
10. Review latest audit events from Settings.
```

### Production Readiness Checklist

Before deploying to production:

```text
1. Set DEBUG=False in backend/.env.
2. Set a strong SECRET_KEY.
3. Add production domain/IP to ALLOWED_HOSTS.
4. Add frontend production URL to CORS_ALLOWED_ORIGINS.
5. Use strong PostgreSQL username/password.
6. Run migrations.
7. Create superuser.
8. Create first organization owner.
9. Schedule PostgreSQL backups using cron or Windows Task Scheduler.
10. Store backup files outside the application directory.
11. Test backup restore before client delivery.
12. Put Nginx/Apache/Caddy reverse proxy in front of backend/frontend.
13. Enable HTTPS.
14. Configure server firewall.
15. Keep database access private to the server/VPC.
```

### Run

```bash
cd employee_saas_product
cp backend/.env.example backend/.env
docker compose up --build
```

Then run migrations:

```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```
