from django.contrib import admin
from .models import PerformanceCycle, PerformanceGoal, PerformanceReview


@admin.register(PerformanceCycle)
class PerformanceCycleAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'year', 'period', 'status', 'start_date', 'end_date')
    list_filter = ('organization', 'year', 'period', 'status')
    search_fields = ('name', 'description')


@admin.register(PerformanceGoal)
class PerformanceGoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'cycle', 'employee', 'category', 'weightage', 'status')
    list_filter = ('organization', 'cycle', 'category', 'status')
    search_fields = ('title', 'employee__employee_code', 'employee__user__email')


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ('cycle', 'employee', 'manager', 'status', 'manager_rating', 'final_rating', 'final_score')
    list_filter = ('organization', 'cycle', 'status')
    search_fields = ('employee__employee_code', 'employee__user__email', 'manager__user__email')
