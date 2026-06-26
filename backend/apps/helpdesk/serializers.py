from django.utils import timezone
from rest_framework import serializers
from apps.accounts.models import Membership, User
from apps.accounts.permissions import HR_ROLES, IT_ROLES, MANAGER_ROLES, get_role
from apps.hr.models import Employee
from .models import SupportTicket, TicketAttachment, TicketCategory, TicketComment

SUPPORT_ROLES = HR_ROLES | IT_ROLES


class TicketCategorySerializer(serializers.ModelSerializer):
    default_assignee_email = serializers.EmailField(source='default_assignee.email', read_only=True)

    class Meta:
        model = TicketCategory
        fields = [
            'id', 'organization', 'name', 'description', 'default_assignee', 'default_assignee_email',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'default_assignee_email', 'created_at', 'updated_at']

    def validate_default_assignee(self, value):
        request = self.context.get('request')
        if value and request:
            if not Membership.objects.filter(organization=request.user.current_organization, user=value, is_active=True).exists():
                raise serializers.ValidationError('Default assignee must belong to the current organization.')
        return value


class SupportTicketSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()
    requested_by_code = serializers.CharField(source='requested_by.employee_code', read_only=True)
    requested_by_email = serializers.EmailField(source='requested_by.user.email', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    comment_count = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'organization', 'ticket_number', 'requested_by', 'requested_by_name', 'requested_by_code',
            'requested_by_email', 'category', 'category_name', 'assigned_to', 'assigned_to_email', 'subject',
            'description', 'priority', 'status', 'source', 'due_at', 'resolved_at', 'closed_at', 'cancelled_at',
            'resolution_notes', 'last_response_at', 'comment_count', 'attachment_count', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'ticket_number', 'requested_by_name', 'requested_by_code', 'requested_by_email',
            'assigned_to_email', 'category_name', 'status', 'resolved_at', 'closed_at', 'cancelled_at',
            'last_response_at', 'comment_count', 'attachment_count', 'is_overdue', 'created_at', 'updated_at'
        ]

    def get_requested_by_name(self, obj):
        return f'{obj.requested_by.user.first_name} {obj.requested_by.user.last_name}'.strip() or obj.requested_by.user.email

    def get_comment_count(self, obj):
        return getattr(obj, 'comment_count', None) or obj.comments.count()

    def get_attachment_count(self, obj):
        return getattr(obj, 'attachment_count', None) or obj.attachments.count()

    def validate_requested_by(self, value):
        request = self.context.get('request')
        if not request:
            return value
        if value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Employee must belong to the current organization.')
        role = get_role(request.user)
        if role not in SUPPORT_ROLES:
            current_employee = Employee.objects.filter(organization=request.user.current_organization, user=request.user).first()
            if not current_employee or current_employee.pk != value.pk:
                raise serializers.ValidationError('You can create tickets only for yourself.')
        return value

    def validate_category(self, value):
        request = self.context.get('request')
        if value and request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Category must belong to the current organization.')
        return value

    def validate_assigned_to(self, value):
        request = self.context.get('request')
        if value and request:
            if not Membership.objects.filter(organization=request.user.current_organization, user=value, is_active=True).exists():
                raise serializers.ValidationError('Assignee must belong to the current organization.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request and self.instance is None and not attrs.get('requested_by'):
            employee = Employee.objects.filter(organization=request.user.current_organization, user=request.user).first()
            if not employee:
                raise serializers.ValidationError({'requested_by': 'No employee profile is linked to this user.'})
            attrs['requested_by'] = employee
        if self.instance is None and attrs.get('category') and not attrs.get('assigned_to'):
            attrs['assigned_to'] = attrs['category'].default_assignee
        return attrs


class TicketCommentSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source='author.email', read_only=True)
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True)

    class Meta:
        model = TicketComment
        fields = [
            'id', 'organization', 'ticket', 'ticket_number', 'author', 'author_email', 'message',
            'is_internal', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'author', 'author_email', 'ticket_number', 'created_at', 'updated_at']

    def validate_ticket(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Ticket must belong to the current organization.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        role = get_role(request.user) if request else None
        if attrs.get('is_internal') and role not in SUPPORT_ROLES:
            raise serializers.ValidationError({'is_internal': 'Only support users can add internal comments.'})
        return attrs


class TicketAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=True, allow_empty_file=False)
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = TicketAttachment
        fields = [
            'id', 'organization', 'ticket', 'ticket_number', 'uploaded_by', 'uploaded_by_email', 'title',
            'notes', 'file', 'file_name', 'content_type', 'file_size', 'download_url', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'uploaded_by', 'uploaded_by_email', 'ticket_number', 'file_name',
            'content_type', 'file_size', 'download_url', 'created_at', 'updated_at'
        ]

    def get_download_url(self, obj):
        request = self.context.get('request')
        path = f'/api/ticket-attachments/{obj.pk}/download/'
        return request.build_absolute_uri(path) if request else path

    def validate_ticket(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Ticket must belong to the current organization.')
        return value

    def create(self, validated_data):
        uploaded_file = validated_data.pop('file')
        data = uploaded_file.read()
        validated_data['file_name'] = uploaded_file.name
        validated_data['content_type'] = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
        validated_data['file_size'] = getattr(uploaded_file, 'size', None) or len(data)
        validated_data['file_data'] = data
        return super().create(validated_data)


class TicketAssignSerializer(serializers.Serializer):
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    due_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_assigned_to(self, value):
        request = self.context.get('request')
        if value and request:
            if not Membership.objects.filter(organization=request.user.current_organization, user=value, is_active=True).exists():
                raise serializers.ValidationError('Assignee must belong to the current organization.')
        return value


class TicketResolutionSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(required=False, allow_blank=True)


class TicketRejectLikeSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True)
