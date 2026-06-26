from django.utils import timezone
from rest_framework import serializers
from apps.accounts.models import Membership, User
from .models import Announcement, AnnouncementRead, Notification


VALID_ROLES = [choice[0] for choice in Membership.ROLE_CHOICES]


class NotificationSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'organization', 'recipient', 'recipient_email', 'created_by', 'created_by_email',
            'title', 'message', 'notification_type', 'related_module', 'related_object_id',
            'action_url', 'is_read', 'read_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_by', 'created_by_email', 'read_at', 'created_at', 'updated_at']

    def validate_recipient(self, value):
        request = self.context.get('request')
        if not request:
            return value
        if not value.memberships.filter(organization=request.user.current_organization, is_active=True).exists():
            raise serializers.ValidationError('Recipient must belong to the current organization.')
        return value


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    is_active = serializers.SerializerMethodField()
    is_read_by_me = serializers.SerializerMethodField()
    read_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'organization', 'title', 'message', 'audience_roles', 'starts_at', 'expires_at',
            'is_published', 'is_active', 'is_read_by_me', 'read_count', 'created_by', 'created_by_email',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_by', 'created_by_email', 'is_active', 'is_read_by_me', 'read_count', 'created_at', 'updated_at']

    def get_is_active(self, obj):
        return obj.is_active_now()

    def get_is_read_by_me(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        prefetched = getattr(obj, 'my_reads', None)
        if prefetched is not None:
            return bool(prefetched)
        return obj.reads.filter(user=request.user).exists()

    def validate_audience_roles(self, value):
        if value in [None, '']:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('audience_roles must be a list of role codes.')
        invalid = [role for role in value if role not in VALID_ROLES]
        if invalid:
            raise serializers.ValidationError(f'Invalid roles: {", ".join(invalid)}')
        return value

    def validate(self, attrs):
        starts_at = attrs.get('starts_at') or getattr(self.instance, 'starts_at', None)
        expires_at = attrs.get('expires_at') or getattr(self.instance, 'expires_at', None)
        if starts_at and expires_at and expires_at <= starts_at:
            raise serializers.ValidationError({'expires_at': 'Expiry must be after start date/time.'})
        return attrs
