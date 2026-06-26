from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers
from apps.accounts.permissions import HR_ROLES, MANAGER_ROLES, get_role
from apps.hr.models import Employee
from .models import PerformanceCycle, PerformanceGoal, PerformanceReview


class PerformanceCycleSerializer(serializers.ModelSerializer):
    goal_count = serializers.IntegerField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    finalized_count = serializers.IntegerField(read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = PerformanceCycle
        fields = [
            'id', 'organization', 'name', 'year', 'period', 'start_date', 'end_date',
            'self_review_start', 'self_review_end', 'manager_review_start', 'manager_review_end',
            'hr_calibration_start', 'hr_calibration_end', 'status', 'description',
            'created_by', 'created_by_email', 'published_at', 'closed_at',
            'goal_count', 'review_count', 'finalized_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['organization', 'created_by', 'created_by_email', 'published_at', 'closed_at', 'created_at', 'updated_at']

    def validate(self, attrs):
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError('start_date cannot be after end_date.')
        return attrs


class PerformanceGoalSerializer(serializers.ModelSerializer):
    cycle_name = serializers.CharField(source='cycle.name', read_only=True)
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_email = serializers.EmailField(source='employee.user.email', read_only=True)
    manager_email = serializers.EmailField(source='employee.manager.user.email', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True)

    class Meta:
        model = PerformanceGoal
        fields = [
            'id', 'organization', 'cycle', 'cycle_name', 'employee', 'employee_name', 'employee_code', 'employee_email',
            'manager_email', 'title', 'description', 'category', 'weightage', 'target_value', 'measurement_unit',
            'due_date', 'status', 'self_rating', 'self_comment', 'manager_rating', 'manager_comment',
            'rejection_reason', 'created_by', 'created_by_email', 'approved_by', 'approved_by_email',
            'approved_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'organization', 'status', 'self_rating', 'self_comment', 'manager_rating', 'manager_comment',
            'rejection_reason', 'created_by', 'created_by_email', 'approved_by', 'approved_by_email',
            'approved_at', 'created_at', 'updated_at',
        ]

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs
        org = request.user.current_organization
        employee = attrs.get('employee', getattr(self.instance, 'employee', None))
        cycle = attrs.get('cycle', getattr(self.instance, 'cycle', None))
        if employee and employee.organization_id != org.id:
            raise serializers.ValidationError('Employee must belong to your organization.')
        if cycle and cycle.organization_id != org.id:
            raise serializers.ValidationError('Cycle must belong to your organization.')
        if cycle and cycle.status == PerformanceCycle.STATUS_CLOSED:
            raise serializers.ValidationError('Cannot create or update goals for a closed cycle.')
        role = get_role(request.user)
        current_employee = Employee.objects.filter(organization=org, user=request.user).first()
        if role not in HR_ROLES:
            if not current_employee:
                raise serializers.ValidationError('Employee profile not found for the logged-in user.')
            if role in MANAGER_ROLES:
                can_manage = employee and (employee.pk == current_employee.pk or employee.manager_id == current_employee.pk)
                if not can_manage:
                    raise serializers.ValidationError('Managers can create goals only for themselves or their team members.')
            elif employee and employee.pk != current_employee.pk:
                raise serializers.ValidationError('Employees can create goals only for themselves.')
        return attrs


class GoalSelfReviewSerializer(serializers.Serializer):
    self_rating = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('5'))
    self_comment = serializers.CharField(required=False, allow_blank=True)


class GoalManagerReviewSerializer(serializers.Serializer):
    manager_rating = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('5'))
    manager_comment = serializers.CharField(required=False, allow_blank=True)


class GoalRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False)


class PerformanceReviewSerializer(serializers.ModelSerializer):
    cycle_name = serializers.CharField(source='cycle.name', read_only=True)
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_email = serializers.EmailField(source='employee.user.email', read_only=True)
    manager_name = serializers.SerializerMethodField()
    manager_email = serializers.EmailField(source='manager.user.email', read_only=True)
    finalized_by_email = serializers.EmailField(source='finalized_by.email', read_only=True)
    goals_count = serializers.SerializerMethodField()
    approved_goals_count = serializers.SerializerMethodField()
    goal_weightage_total = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceReview
        fields = [
            'id', 'organization', 'cycle', 'cycle_name', 'employee', 'employee_name', 'employee_code', 'employee_email',
            'manager', 'manager_name', 'manager_email', 'status', 'self_summary', 'strengths', 'improvement_areas',
            'career_goals', 'self_submitted_at', 'manager_summary', 'manager_rating', 'manager_submitted_at',
            'hr_comments', 'final_rating', 'final_score', 'finalized_by', 'finalized_by_email', 'finalized_at',
            'goals_count', 'approved_goals_count', 'goal_weightage_total', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'organization', 'status', 'self_summary', 'strengths', 'improvement_areas', 'career_goals',
            'self_submitted_at', 'manager_summary', 'manager_rating', 'manager_submitted_at', 'hr_comments',
            'final_rating', 'final_score', 'finalized_by', 'finalized_by_email', 'finalized_at', 'created_at', 'updated_at',
        ]

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def get_manager_name(self, obj):
        if not obj.manager:
            return ''
        return f'{obj.manager.user.first_name} {obj.manager.user.last_name}'.strip() or obj.manager.user.email

    def get_goals_count(self, obj):
        return PerformanceGoal.objects.filter(organization=obj.organization, cycle=obj.cycle, employee=obj.employee).count()

    def get_approved_goals_count(self, obj):
        return PerformanceGoal.objects.filter(organization=obj.organization, cycle=obj.cycle, employee=obj.employee, status=PerformanceGoal.STATUS_APPROVED).count()

    def get_goal_weightage_total(self, obj):
        value = PerformanceGoal.objects.filter(organization=obj.organization, cycle=obj.cycle, employee=obj.employee).aggregate(total=Sum('weightage'))['total']
        return value or Decimal('0.00')

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs
        org = request.user.current_organization
        employee = attrs.get('employee', getattr(self.instance, 'employee', None))
        cycle = attrs.get('cycle', getattr(self.instance, 'cycle', None))
        manager = attrs.get('manager', getattr(self.instance, 'manager', None))
        if employee and employee.organization_id != org.id:
            raise serializers.ValidationError('Employee must belong to your organization.')
        if cycle and cycle.organization_id != org.id:
            raise serializers.ValidationError('Cycle must belong to your organization.')
        if manager and manager.organization_id != org.id:
            raise serializers.ValidationError('Manager must belong to your organization.')
        role = get_role(request.user)
        current_employee = Employee.objects.filter(organization=org, user=request.user).first()
        if role not in HR_ROLES:
            if not current_employee:
                raise serializers.ValidationError('Employee profile not found for the logged-in user.')
            if role in MANAGER_ROLES:
                can_manage = employee and (employee.pk == current_employee.pk or employee.manager_id == current_employee.pk)
                if not can_manage:
                    raise serializers.ValidationError('Managers can create reviews only for themselves or their team members.')
            elif employee and employee.pk != current_employee.pk:
                raise serializers.ValidationError('Employees can create reviews only for themselves.')
        return attrs


class SelfReviewSubmitSerializer(serializers.Serializer):
    self_summary = serializers.CharField(required=True, allow_blank=False)
    strengths = serializers.CharField(required=False, allow_blank=True)
    improvement_areas = serializers.CharField(required=False, allow_blank=True)
    career_goals = serializers.CharField(required=False, allow_blank=True)


class ManagerReviewSubmitSerializer(serializers.Serializer):
    manager_summary = serializers.CharField(required=True, allow_blank=False)
    manager_rating = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('5'))


class FinalizeReviewSerializer(serializers.Serializer):
    hr_comments = serializers.CharField(required=False, allow_blank=True)
    final_rating = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('5'))
    final_score = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('100'))
