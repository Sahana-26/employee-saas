from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import get_valid_filename
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from apps.accounts.models import Membership
from apps.accounts.permissions import HR_ROLES, IsHR, IsOrganizationMember, get_role
from apps.notifications.services import notify_roles
from .models import CompanyPolicy, PolicyAcknowledgement
from .serializers import CompanyPolicySerializer, PolicyAcknowledgementSerializer


class CompanyPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyPolicySerializer
    permission_classes = [IsOrganizationMember]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        org = self.request.user.current_organization
        role = get_role(self.request.user)
        qs = (
            CompanyPolicy.objects
            .filter(organization=org)
            .annotate(acknowledgement_count=Count('acknowledgements'))
            .select_related('created_by')
            .prefetch_related(Prefetch('acknowledgements', queryset=PolicyAcknowledgement.objects.filter(user=self.request.user), to_attr='my_acknowledgements'))
            .defer('document_data')
        )
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        if role in HR_ROLES:
            return qs
        ids = [policy.id for policy in qs if policy.is_published and policy.applies_to_role(role)]
        return qs.filter(id__in=ids)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'publish', 'archive', 'acknowledgements']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        policy = serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)
        if policy.is_published:
            self._notify_policy_audience(policy, self.request)

    def _notify_policy_audience(self, policy, request):
        roles = policy.audience_roles or [choice[0] for choice in Membership.ROLE_CHOICES]
        notify_roles(
            policy.organization,
            roles,
            title='New company policy published',
            message=f'{policy.title} v{policy.version} has been published. Please review and acknowledge it if required.',
            notification_type='ACTION' if policy.requires_acknowledgement else 'INFO',
            related_module='policies',
            related_object_id=policy.pk,
            action_url='/policies',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        policy = self.get_object()
        policy.publish()
        self._notify_policy_audience(policy, request)
        return Response(CompanyPolicySerializer(policy, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        policy = self.get_object()
        policy.archive()
        return Response(CompanyPolicySerializer(policy, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        policy = self.get_object()
        if not policy.is_published:
            return Response({'detail': 'Only published policies can be acknowledged.'}, status=status.HTTP_400_BAD_REQUEST)
        role = get_role(request.user)
        if not policy.applies_to_role(role):
            return Response({'detail': 'This policy is not assigned to your role.'}, status=status.HTTP_403_FORBIDDEN)
        acknowledgement, created = PolicyAcknowledgement.objects.get_or_create(
            organization=request.user.current_organization,
            policy=policy,
            user=request.user,
            defaults={
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:1000],
            },
        )
        serializer = PolicyAcknowledgementSerializer(acknowledgement, context={'request': request})
        return Response({'detail': 'Policy acknowledged.' if created else 'Policy was already acknowledged.', 'acknowledgement': serializer.data})

    @action(detail=False, methods=['get'], url_path='pending-acknowledgements')
    def pending_acknowledgements(self, request):
        org = request.user.current_organization
        role = get_role(request.user)
        base = (
            CompanyPolicy.objects
            .filter(organization=org, is_published=True, requires_acknowledgement=True)
            .annotate(acknowledgement_count=Count('acknowledgements'))
            .prefetch_related(Prefetch('acknowledgements', queryset=PolicyAcknowledgement.objects.filter(user=request.user), to_attr='my_acknowledgements'))
            .defer('document_data')
        )
        ids = [policy.id for policy in base if policy.applies_to_role(role)]
        acknowledged_ids = PolicyAcknowledgement.objects.filter(organization=org, user=request.user).values_list('policy_id', flat=True)
        qs = base.filter(id__in=ids).exclude(id__in=acknowledged_ids)
        serializer = CompanyPolicySerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='acknowledgements')
    def acknowledgements(self, request, pk=None):
        policy = self.get_object()
        acknowledgements = policy.acknowledgements.filter(organization=request.user.current_organization).select_related('user', 'policy')
        serializer = PolicyAcknowledgementSerializer(acknowledgements, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='download-document')
    def download_document(self, request, pk=None):
        policy = get_object_or_404(CompanyPolicy, pk=pk, organization=request.user.current_organization)
        role = get_role(request.user)
        if role not in HR_ROLES and (not policy.is_published or not policy.applies_to_role(role)):
            return Response({'detail': 'You do not have permission to download this policy document.'}, status=status.HTTP_403_FORBIDDEN)
        if not policy.document_data:
            return Response({'detail': 'No document is attached to this policy.'}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(bytes(policy.document_data), content_type=policy.document_content_type or 'application/octet-stream')
        file_name = get_valid_filename(policy.document_file_name or f'policy-{policy.pk}')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
