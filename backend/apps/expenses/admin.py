from django.contrib import admin
from .models import ExpenseCategory, ExpenseClaim


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'is_active')
    search_fields = ('name', 'organization__name')
    list_filter = ('is_active',)


@admin.register(ExpenseClaim)
class ExpenseClaimAdmin(admin.ModelAdmin):
    list_display = ('claim_number', 'employee', 'title', 'amount', 'status', 'expense_date', 'organization')
    search_fields = ('claim_number', 'title', 'employee__employee_code', 'employee__user__email')
    list_filter = ('status', 'expense_date', 'category')
    readonly_fields = ('receipt_data',)
