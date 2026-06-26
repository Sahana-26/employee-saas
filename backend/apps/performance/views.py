from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.models import Membership
from apps.accounts.permissions import HR_ROLES, MANAGER_ROLES, IsHR, IsManagerLevel, IsOrganizationMember, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles
from .models import PerformanceCycle, PerformanceGoal, PerformanceReview
from .serializers import (
    FinalizeReviewSerializer,
    GoalManagerReviewSerializer,
    GoalRejectSerializer,
    GoalSelfReviewSerializer,
    ManagerReviewSubmitSerializer,
    PerformanceCycleSerializer,
    PerformanceGoalSerializer,
    PerformanceReviewSerializer,
    SelfReviewSubmitSerializer,
)


class PerformanceCycleViewSet(viewsets.ModelViewSet):
    serializer_class = PerformanceCycleSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        return (
            PerformanceCycle.objects
            .filter(organization=self.request.user.current_organization)
            .annotate(
                goal_count=Count('goals', distinct=True),
                review_count=Count('reviews', distinct=True),
                finalized_count=Count('reviews', filter=Q(reviews__status=PerformanceReview.STATUS_FINALIZED), distinct=True),
            )
            .select_related('created_by')
        )

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'publish', 'close']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)

    def _notify_cycle_audience(self, cycle, request):
        roles = [choice[0] for choice in Membership.ROLE_CHOICES]
        notify_roles(
            cycle.organization,
            roles,
            title='Performance cycle published',
            message=f'{cycle.name} {cycle.year} is now active. Please review your goals and appraisal tasks.',
            notification_type='ACTION',
            related_module='performance',
            related_object_id=cycle.pk,
            action_url='/performance',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        cycle = self.get_object()
        cycle.publish()
        self._notify_cycle_audience(cycle, request)
        return Response(PerformanceCycleSerializer(cycle, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        cycle = self.get_object()
        cycle.close()
        return Response(PerformanceCycleSerializer(cycle, context={'request': request}).data)


class PerformanceGoalViewSet(viewsets.ModelViewSet):
    serializer_class = PerformanceGoalSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = (
            PerformanceGoal.objects
            .filter(organization=org)
            .select_related('cycle', 'employee__user', 'employee__manager__user', 'created_by', 'approved_by')
        )
        cycle_id = self.request.query_params.get('cycle')
        employee_id = self.request.query_params.get('employee')
        status_value = self.request.query_params.get('status')
        if cycle_id:
            qs = qs.filter(cycle_id=cycle_id)
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if status_value:
            qs = qs.filter(status=status_value)
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(Q(employee=current_employee) | Q(employee__manager=current_employee)).distinct()
        if current_employee:
            return qs.filter(employee=current_employee)
        return qs.none()

    def perform_create(self, serializer):
        goal = serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)
        PerformanceReview.objects.get_or_create(
            organization=goal.organization,
            cycle=goal.cycle,
            employee=goal.employee,
            defaults={'manager': goal.employee.manager},
        )

    def _can_manage_goal(self, goal):
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return True
        current_employee = Employee.objects.filter(organization=goal.organization, user=self.request.user).first()
        return bool(role in MANAGER_ROLES and current_employee and goal.employee.manager_id == current_employee.pk)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        goal = self.get_object()
        if goal.status not in [PerformanceGoal.STATUS_DRAFT, PerformanceGoal.STATUS_REJECTED]:
            return Response({'detail': 'Only draft or rejected goals can be submitted.'}, status=status.HTTP_400_BAD_REQUEST)
        current_employee = Employee.objects.filter(organization=goal.organization, user=request.user).first()
        role = get_role(request.user)
        if role not in HR_ROLES and not (current_employee and (goal.employee_id == current_employee.pk or goal.employee.manager_id == current_employee.pk)):
            return Response({'detail': 'You do not have permission to submit this goal.'}, status=status.HTTP_403_FORBIDDEN)
        goal.status = PerformanceGoal.STATUS_SUBMITTED
        goal.rejection_reason = ''
        goal.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        if goal.employee.manager:
            notify_employee(
                goal.employee.manager,
                title='Performance goal submitted',
                message=f'{goal.employee.user.email} submitted goal: {goal.title}.',
                notification_type='ACTION',
                related_module='performance',
                related_object_id=goal.pk,
                action_url='/performance',
                created_by=request.user,
            )
        notify_roles(
            goal.organization,
            ['OWNER', 'ADMIN', 'HR'],
            title='Performance goal submitted',
            message=f'{goal.employee.user.email} submitted a performance goal for {goal.cycle.name}.',
            notification_type='ACTION',
            related_module='performance',
            related_object_id=goal.pk,
            action_url='/performance',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )
        return Response({'detail': 'Goal submitted.'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        goal = self.get_object()
        if not self._can_manage_goal(goal):
            return Response({'detail': 'You do not have permission to approve this goal.'}, status=status.HTTP_403_FORBIDDEN)
        if goal.status != PerformanceGoal.STATUS_SUBMITTED:
            return Response({'detail': 'Only submitted goals can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        goal.status = PerformanceGoal.STATUS_APPROVED
        goal.approved_by = request.user
        goal.approved_at = timezone.now()
        goal.rejection_reason = ''
        goal.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_reason', 'updated_at'])
        notify_employee(
            goal.employee,
            title='Performance goal approved',
            message=f'Your goal "{goal.title}" has been approved.',
            notification_type='SUCCESS',
            related_module='performance',
            related_object_id=goal.pk,
            action_url='/performance',
            created_by=request.user,
        )
        return Response({'detail': 'Goal approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        goal = self.get_object()
        if not self._can_manage_goal(goal):
            return Response({'detail': 'You do not have permission to reject this goal.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = GoalRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        goal.status = PerformanceGoal.STATUS_REJECTED
        goal.rejection_reason = serializer.validated_data['reason']
        goal.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        notify_employee(
            goal.employee,
            title='Performance goal rejected',
            message=f'Your goal "{goal.title}" was rejected. {goal.rejection_reason}',
            notification_type='WARNING',
            related_module='performance',
            related_object_id=goal.pk,
            action_url='/performance',
            created_by=request.user,
        )
        return Response({'detail': 'Goal rejected.'})

    @action(detail=True, methods=['post'], url_path='self-review')
    def self_review(self, request, pk=None):
        goal = self.get_object()
        current_employee = Employee.objects.filter(organization=goal.organization, user=request.user).first()
        if not current_employee or goal.employee_id != current_employee.pk:
            return Response({'detail': 'You can self-review only your own goal.'}, status=status.HTTP_403_FORBIDDEN)
        if goal.status != PerformanceGoal.STATUS_APPROVED:
            return Response({'detail': 'Only approved goals can be self-reviewed.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = GoalSelfReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        goal.self_rating = serializer.validated_data['self_rating']
        goal.self_comment = serializer.validated_data.get('self_comment', '')
        goal.save(update_fields=['self_rating', 'self_comment', 'updated_at'])
        return Response({'detail': 'Goal self-review saved.'})

    @action(detail=True, methods=['post'], url_path='manager-review')
    def manager_review(self, request, pk=None):
        goal = self.get_object()
        if not self._can_manage_goal(goal):
            return Response({'detail': 'You do not have permission to review this goal.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = GoalManagerReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        goal.manager_rating = serializer.validated_data['manager_rating']
        goal.manager_comment = serializer.validated_data.get('manager_comment', '')
        goal.save(update_fields=['manager_rating', 'manager_comment', 'updated_at'])
        return Response({'detail': 'Manager goal review saved.'})


class PerformanceReviewViewSet(viewsets.ModelViewSet):
    serializer_class = PerformanceReviewSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = (
            PerformanceReview.objects
            .filter(organization=org)
            .select_related('cycle', 'employee__user', 'manager__user', 'finalized_by')
        )
        cycle_id = self.request.query_params.get('cycle')
        employee_id = self.request.query_params.get('employee')
        status_value = self.request.query_params.get('status')
        if cycle_id:
            qs = qs.filter(cycle_id=cycle_id)
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if status_value:
            qs = qs.filter(status=status_value)
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(Q(employee=current_employee) | Q(manager=current_employee) | Q(employee__manager=current_employee)).distinct()
        if current_employee:
            return qs.filter(employee=current_employee)
        return qs.none()

    def perform_create(self, serializer):
        review = serializer.save(organization=self.request.user.current_organization)
        if not review.manager_id:
            review.manager = review.employee.manager
            review.save(update_fields=['manager', 'updated_at'])

    def _can_manage_review(self, review):
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return True
        current_employee = Employee.objects.filter(organization=review.organization, user=self.request.user).first()
        return bool(role in MANAGER_ROLES and current_employee and (review.manager_id == current_employee.pk or review.employee.manager_id == current_employee.pk))

    def get_permissions(self):
        if self.action in ['finalize']:
            return [IsHR()]
        return super().get_permissions()

    @action(detail=True, methods=['post'], url_path='submit-self-review')
    def submit_self_review(self, request, pk=None):
        review = self.get_object()
        current_employee = Employee.objects.filter(organization=review.organization, user=request.user).first()
        if not current_employee or review.employee_id != current_employee.pk:
            return Response({'detail': 'You can submit only your own self-review.'}, status=status.HTTP_403_FORBIDDEN)
        if review.cycle.status != PerformanceCycle.STATUS_ACTIVE:
            return Response({'detail': 'Self-review can be submitted only for active cycles.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SelfReviewSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review.self_summary = serializer.validated_data['self_summary']
        review.strengths = serializer.validated_data.get('strengths', '')
        review.improvement_areas = serializer.validated_data.get('improvement_areas', '')
        review.career_goals = serializer.validated_data.get('career_goals', '')
        review.status = PerformanceReview.STATUS_SELF_REVIEW
        review.self_submitted_at = timezone.now()
        review.save(update_fields=['self_summary', 'strengths', 'improvement_areas', 'career_goals', 'status', 'self_submitted_at', 'updated_at'])
        if review.manager:
            notify_employee(
                review.manager,
                title='Self-review submitted',
                message=f'{review.employee.user.email} submitted self-review for {review.cycle.name}.',
                notification_type='ACTION',
                related_module='performance',
                related_object_id=review.pk,
                action_url='/performance',
                created_by=request.user,
            )
        return Response({'detail': 'Self-review submitted.'})

    @action(detail=True, methods=['post'], url_path='submit-manager-review')
    def submit_manager_review(self, request, pk=None):
        review = self.get_object()
        if not self._can_manage_review(review):
            return Response({'detail': 'You do not have permission to submit manager review.'}, status=status.HTTP_403_FORBIDDEN)
        if review.status not in [PerformanceReview.STATUS_SELF_REVIEW, PerformanceReview.STATUS_MANAGER_REVIEW, PerformanceReview.STATUS_HR_REVIEW]:
            return Response({'detail': 'Self-review must be submitted before manager review.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ManagerReviewSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review.manager_summary = serializer.validated_data['manager_summary']
        review.manager_rating = serializer.validated_data['manager_rating']
        review.status = PerformanceReview.STATUS_MANAGER_REVIEW
        review.manager = review.manager or review.employee.manager
        review.manager_submitted_at = timezone.now()
        review.save(update_fields=['manager_summary', 'manager_rating', 'status', 'manager', 'manager_submitted_at', 'updated_at'])
        notify_employee(
            review.employee,
            title='Manager review submitted',
            message=f'Manager review for {review.cycle.name} has been submitted.',
            notification_type='INFO',
            related_module='performance',
            related_object_id=review.pk,
            action_url='/performance',
            created_by=request.user,
        )
        notify_roles(
            review.organization,
            ['OWNER', 'ADMIN', 'HR'],
            title='Performance review ready for HR calibration',
            message=f'{review.employee.user.email} review is ready for HR finalization.',
            notification_type='ACTION',
            related_module='performance',
            related_object_id=review.pk,
            action_url='/performance',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )
        return Response({'detail': 'Manager review submitted.'})

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        review = self.get_object()
        if review.status not in [PerformanceReview.STATUS_MANAGER_REVIEW, PerformanceReview.STATUS_HR_REVIEW, PerformanceReview.STATUS_FINALIZED]:
            return Response({'detail': 'Manager review must be submitted before finalization.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = FinalizeReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review.hr_comments = serializer.validated_data.get('hr_comments', '')
        review.final_rating = serializer.validated_data['final_rating']
        review.final_score = serializer.validated_data['final_score']
        review.status = PerformanceReview.STATUS_FINALIZED
        review.finalized_by = request.user
        review.finalized_at = timezone.now()
        review.save(update_fields=['hr_comments', 'final_rating', 'final_score', 'status', 'finalized_by', 'finalized_at', 'updated_at'])
        notify_employee(
            review.employee,
            title='Performance review finalized',
            message=f'Your final appraisal rating for {review.cycle.name} has been published.',
            notification_type='SUCCESS',
            related_module='performance',
            related_object_id=review.pk,
            action_url='/performance',
            created_by=request.user,
        )
        return Response({'detail': 'Performance review finalized.'})
