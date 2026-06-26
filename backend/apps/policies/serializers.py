import json
from django.utils import timezone
from rest_framework import serializers
from apps.accounts.models import Membership
from .models import CompanyPolicy, PolicyAcknowledgement


VALID_ROLES = [choice[0] for choice in Membership.ROLE_CHOICES]


class CompanyPolicySerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    document = serializers.FileField(write_only=True, required=False, allow_empty_file=False)
    clear_document = serializers.BooleanField(write_only=True, required=False, default=False)
    has_document = serializers.SerializerMethodField()
    document_download_url = serializers.SerializerMethodField()
    acknowledgement_count = serializers.IntegerField(read_only=True)
    is_acknowledged_by_me = serializers.SerializerMethodField()

    class Meta:
        model = CompanyPolicy
        fields = [
            'id', 'organization', 'title', 'code', 'version', 'category', 'summary', 'content',
            'audience_roles', 'requires_acknowledgement', 'is_published', 'published_at', 'archived_at',
            'document', 'clear_document', 'document_file_name', 'document_content_type', 'document_size',
            'has_document', 'document_download_url', 'acknowledgement_count', 'is_acknowledged_by_me',
            'created_by', 'created_by_email', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'published_at', 'archived_at', 'document_file_name',
            'document_content_type', 'document_size', 'has_document', 'document_download_url',
            'acknowledgement_count', 'is_acknowledged_by_me', 'created_by', 'created_by_email',
            'created_at', 'updated_at',
        ]

    def get_has_document(self, obj):
        return bool(obj.document_size)

    def get_document_download_url(self, obj):
        if not obj.document_size:
            return ''
        return f'/policies/{obj.id}/download-document/'

    def get_is_acknowledged_by_me(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        prefetched = getattr(obj, 'my_acknowledgements', None)
        if prefetched is not None:
            return bool(prefetched)
        return obj.acknowledgements.filter(user=request.user).exists()

    def validate_audience_roles(self, value):
        if value in [None, '']:
            return []
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError('audience_roles must be a valid JSON list of role codes.') from exc
        if not isinstance(value, list):
            raise serializers.ValidationError('audience_roles must be a list of role codes.')
        invalid = [role for role in value if role not in VALID_ROLES]
        if invalid:
            raise serializers.ValidationError(f'Invalid roles: {", ".join(invalid)}')
        return value

    def _apply_document(self, instance, document):
        if not document:
            return
        data = document.read()
        instance.document_data = data
        instance.document_file_name = document.name
        instance.document_content_type = getattr(document, 'content_type', '') or 'application/octet-stream'
        instance.document_size = len(data)

    def create(self, validated_data):
        document = validated_data.pop('document', None)
        validated_data.pop('clear_document', None)
        instance = CompanyPolicy(**validated_data)
        if instance.is_published and not instance.published_at:
            instance.published_at = timezone.now()
            instance.archived_at = None
        self._apply_document(instance, document)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        document = validated_data.pop('document', None)
        clear_document = validated_data.pop('clear_document', False)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if clear_document:
            instance.document_data = None
            instance.document_file_name = ''
            instance.document_content_type = ''
            instance.document_size = 0
        if instance.is_published and not instance.published_at:
            instance.published_at = timezone.now()
            instance.archived_at = None
        self._apply_document(instance, document)
        instance.save()
        return instance


class PolicyAcknowledgementSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    policy_code = serializers.CharField(source='policy.code', read_only=True)
    policy_version = serializers.CharField(source='policy.version', read_only=True)

    class Meta:
        model = PolicyAcknowledgement
        fields = [
            'id', 'organization', 'policy', 'policy_title', 'policy_code', 'policy_version',
            'user', 'user_email', 'acknowledged_at', 'ip_address', 'user_agent',
        ]
        read_only_fields = fields
