from django.contrib import admin
from .models import Candidate, InterviewRound, JobOpening, OfferLetter


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ('job_code', 'title', 'organization', 'department', 'status', 'openings_count', 'created_at')
    list_filter = ('status', 'employment_type', 'work_mode')
    search_fields = ('job_code', 'title', 'location')


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'organization', 'job_opening', 'status', 'source', 'created_at')
    list_filter = ('status', 'source')
    search_fields = ('first_name', 'last_name', 'email', 'phone')


@admin.register(InterviewRound)
class InterviewRoundAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'round_type', 'interviewer', 'status', 'result', 'scheduled_at')
    list_filter = ('round_type', 'status', 'result', 'mode')
    search_fields = ('candidate__first_name', 'candidate__last_name', 'candidate__email')


@admin.register(OfferLetter)
class OfferLetterAdmin(admin.ModelAdmin):
    list_display = ('offer_number', 'candidate', 'job_opening', 'status', 'joining_date', 'ctc')
    list_filter = ('status',)
    search_fields = ('offer_number', 'candidate__first_name', 'candidate__last_name', 'candidate__email')
