from django.contrib import admin
from .models import TrainingAssessment, TrainingCertificate, TrainingCourse, TrainingEnrollment, TrainingMaterial, TrainingSubmission


@admin.register(TrainingCourse)
class TrainingCourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'organization', 'category', 'level', 'status', 'is_mandatory')
    search_fields = ('code', 'title', 'category')
    list_filter = ('status', 'level', 'is_mandatory')


@admin.register(TrainingMaterial)
class TrainingMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'organization', 'material_type', 'file_name')
    search_fields = ('title', 'course__title')


@admin.register(TrainingEnrollment)
class TrainingEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'course', 'organization', 'status', 'progress_percent', 'due_date')
    list_filter = ('status',)
    search_fields = ('employee__employee_code', 'employee__user__email', 'course__title')


@admin.register(TrainingAssessment)
class TrainingAssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'organization', 'max_score', 'passing_score', 'is_published')
    list_filter = ('is_published',)


@admin.register(TrainingSubmission)
class TrainingSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'employee', 'organization', 'score', 'status', 'submitted_at')
    list_filter = ('status',)


@admin.register(TrainingCertificate)
class TrainingCertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_number', 'employee', 'course', 'organization', 'issued_at')
    search_fields = ('certificate_number', 'employee__employee_code', 'employee__user__email')
