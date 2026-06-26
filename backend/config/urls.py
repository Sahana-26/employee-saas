from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from apps.accounts.views import OrganizationViewSet, MembershipViewSet, RegisterOrganizationView, MeView, CustomTokenObtainPairView
from apps.hr.views import DepartmentViewSet, EmployeeViewSet
from apps.attendance.views import AttendanceViewSet, ShiftViewSet, HolidayViewSet, EmployeeShiftAssignmentViewSet, CheckInView, CheckOutView, MyShiftView
from apps.leaves.views import LeaveTypeViewSet, LeaveBalanceViewSet, LeaveRequestViewSet
from apps.payroll.views import PayrollComponentViewSet, EmployeeSalaryComponentViewSet, PayrollRecordViewSet, PayrollRunViewSet, PayslipViewSet
from apps.documents.views import EmployeeDocumentViewSet
from apps.audit.views import AuditLogViewSet
from apps.reports.views import DashboardSummaryView, MonthlyAttendanceReportView, LeaveBalanceReportView
from apps.selfservice.views import MyProfileView, ProfileChangeRequestViewSet
from apps.expenses.views import ExpenseCategoryViewSet, ExpenseClaimViewSet
from apps.notifications.views import AnnouncementViewSet, NotificationViewSet
from apps.policies.views import CompanyPolicyViewSet
from apps.performance.views import PerformanceCycleViewSet, PerformanceGoalViewSet, PerformanceReviewViewSet
from apps.assets.views import AssetCategoryViewSet, AssetViewSet, AssetAssignmentViewSet, AssetDocumentViewSet, AssetMaintenanceViewSet
from apps.offboarding.views import OffboardingCaseViewSet, ClearanceTaskViewSet, FinalSettlementViewSet, OffboardingDocumentViewSet
from apps.recruitment.views import CandidateViewSet, InterviewRoundViewSet, JobOpeningViewSet, OfferLetterViewSet
from apps.training.views import TrainingAssessmentViewSet, TrainingCertificateViewSet, TrainingCourseViewSet, TrainingEnrollmentViewSet, TrainingMaterialViewSet, TrainingSubmissionViewSet
from apps.helpdesk.views import SupportTicketViewSet, TicketAttachmentViewSet, TicketCategoryViewSet, TicketCommentViewSet
from apps.timesheets.views import ProjectMembershipViewSet, ProjectTaskViewSet, TimesheetEntryViewSet, TimesheetMonthlySummaryView, WorkProjectViewSet
from apps.hrletters.views import GeneratedLetterViewSet, LetterTemplateViewSet
from apps.systemsettings.views import BackupLogViewSet, OrganizationSettingView, SystemHealthView, SystemOverviewView

router = DefaultRouter()
router.register('organizations', OrganizationViewSet, basename='organizations')
router.register('memberships', MembershipViewSet, basename='memberships')
router.register('departments', DepartmentViewSet, basename='departments')
router.register('employees', EmployeeViewSet, basename='employees')
router.register('attendance', AttendanceViewSet, basename='attendance')
router.register('shifts', ShiftViewSet, basename='shifts')
router.register('holidays', HolidayViewSet, basename='holidays')
router.register('shift-assignments', EmployeeShiftAssignmentViewSet, basename='shift-assignments')
router.register('leave-types', LeaveTypeViewSet, basename='leave-types')
router.register('leave-balances', LeaveBalanceViewSet, basename='leave-balances')
router.register('leave-requests', LeaveRequestViewSet, basename='leave-requests')
router.register('payroll-records', PayrollRecordViewSet, basename='payroll-records')
router.register('payroll-components', PayrollComponentViewSet, basename='payroll-components')
router.register('salary-components', EmployeeSalaryComponentViewSet, basename='salary-components')
router.register('payroll-runs', PayrollRunViewSet, basename='payroll-runs')
router.register('payslips', PayslipViewSet, basename='payslips')
router.register('documents', EmployeeDocumentViewSet, basename='documents')
router.register('audit-logs', AuditLogViewSet, basename='audit-logs')
router.register('profile-change-requests', ProfileChangeRequestViewSet, basename='profile-change-requests')
router.register('expense-categories', ExpenseCategoryViewSet, basename='expense-categories')
router.register('expenses', ExpenseClaimViewSet, basename='expenses')
router.register('notifications', NotificationViewSet, basename='notifications')
router.register('announcements', AnnouncementViewSet, basename='announcements')
router.register('policies', CompanyPolicyViewSet, basename='policies')
router.register('performance-cycles', PerformanceCycleViewSet, basename='performance-cycles')
router.register('performance-goals', PerformanceGoalViewSet, basename='performance-goals')
router.register('performance-reviews', PerformanceReviewViewSet, basename='performance-reviews')
router.register('asset-categories', AssetCategoryViewSet, basename='asset-categories')
router.register('assets', AssetViewSet, basename='assets')
router.register('asset-assignments', AssetAssignmentViewSet, basename='asset-assignments')
router.register('asset-documents', AssetDocumentViewSet, basename='asset-documents')
router.register('asset-maintenance', AssetMaintenanceViewSet, basename='asset-maintenance')
router.register('offboarding-cases', OffboardingCaseViewSet, basename='offboarding-cases')
router.register('offboarding-clearance', ClearanceTaskViewSet, basename='offboarding-clearance')
router.register('final-settlements', FinalSettlementViewSet, basename='final-settlements')
router.register('offboarding-documents', OffboardingDocumentViewSet, basename='offboarding-documents')
router.register('job-openings', JobOpeningViewSet, basename='job-openings')
router.register('candidates', CandidateViewSet, basename='candidates')
router.register('interviews', InterviewRoundViewSet, basename='interviews')
router.register('offers', OfferLetterViewSet, basename='offers')
router.register('training-courses', TrainingCourseViewSet, basename='training-courses')
router.register('training-materials', TrainingMaterialViewSet, basename='training-materials')
router.register('training-enrollments', TrainingEnrollmentViewSet, basename='training-enrollments')
router.register('training-assessments', TrainingAssessmentViewSet, basename='training-assessments')
router.register('training-submissions', TrainingSubmissionViewSet, basename='training-submissions')
router.register('training-certificates', TrainingCertificateViewSet, basename='training-certificates')
router.register('ticket-categories', TicketCategoryViewSet, basename='ticket-categories')
router.register('support-tickets', SupportTicketViewSet, basename='support-tickets')
router.register('ticket-comments', TicketCommentViewSet, basename='ticket-comments')
router.register('ticket-attachments', TicketAttachmentViewSet, basename='ticket-attachments')
router.register('work-projects', WorkProjectViewSet, basename='work-projects')
router.register('project-memberships', ProjectMembershipViewSet, basename='project-memberships')
router.register('project-tasks', ProjectTaskViewSet, basename='project-tasks')
router.register('timesheet-entries', TimesheetEntryViewSet, basename='timesheet-entries')
router.register('hr-letter-templates', LetterTemplateViewSet, basename='hr-letter-templates')
router.register('generated-letters', GeneratedLetterViewSet, basename='generated-letters')
router.register('backup-logs', BackupLogViewSet, basename='backup-logs')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register-organization/', RegisterOrganizationView.as_view()),
    path('api/auth/token/', CustomTokenObtainPairView.as_view()),
    path('api/auth/token/refresh/', TokenRefreshView.as_view()),
    path('api/auth/me/', MeView.as_view()),
    path('api/attendance/check-in/', CheckInView.as_view()),
    path('api/attendance/check-out/', CheckOutView.as_view()),
    path('api/attendance/my-shift/', MyShiftView.as_view()),
    path('api/reports/dashboard-summary/', DashboardSummaryView.as_view()),
    path('api/reports/monthly-attendance/', MonthlyAttendanceReportView.as_view()),
    path('api/reports/leave-balances/', LeaveBalanceReportView.as_view()),
    path('api/profile/me/', MyProfileView.as_view()),
    path('api/timesheets/monthly-summary/', TimesheetMonthlySummaryView.as_view()),
    path('api/system/settings/', OrganizationSettingView.as_view()),
    path('api/system/health/', SystemHealthView.as_view()),
    path('api/system/overview/', SystemOverviewView.as_view()),
    path('api/', include(router.urls)),
]

