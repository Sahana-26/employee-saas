from django.contrib import admin
from .models import (
    EmployeeSalaryComponent,
    PayrollComponent,
    PayrollRecord,
    PayrollRun,
    Payslip,
    PayslipLine,
)


class PayslipLineInline(admin.TabularInline):
    model = PayslipLine
    extra = 0
    readonly_fields = ['organization', 'component', 'name', 'line_type', 'amount', 'notes']


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month', 'year', 'net_pay', 'status']
    list_filter = ['organization', 'year', 'month', 'status']


@admin.register(PayrollComponent)
class PayrollComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'component_type', 'calculation_type', 'default_amount', 'default_percent', 'is_active']
    list_filter = ['organization', 'component_type', 'calculation_type', 'is_active']


@admin.register(EmployeeSalaryComponent)
class EmployeeSalaryComponentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'component', 'amount', 'percent', 'effective_from', 'effective_to', 'is_active']
    list_filter = ['organization', 'component__component_type', 'is_active']


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ['organization', 'month', 'year', 'status', 'generated_at', 'approved_at', 'paid_at']
    list_filter = ['organization', 'year', 'month', 'status']


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month', 'year', 'gross_earnings', 'total_deductions', 'net_pay', 'status']
    list_filter = ['organization', 'year', 'month', 'status']
    inlines = [PayslipLineInline]
