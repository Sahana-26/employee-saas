from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'organization', 'actor', 'actor_email', 'action', 'entity', 'entity_id', 'metadata', 'ip_address', 'created_at']
        read_only_fields = fields
