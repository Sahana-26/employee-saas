from rest_framework import serializers
from .models import EmployeeDocument


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    employee_name = serializers.SerializerMethodField()
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocument
        fields = [
            'id', 'organization', 'employee', 'employee_name', 'title', 'category', 'file',
            'file_name', 'content_type', 'size', 'download_url', 'uploaded_by', 'uploaded_by_email',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'file_name', 'content_type', 'size', 'download_url',
            'uploaded_by', 'uploaded_by_email', 'created_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        first_name = obj.employee.user.first_name or ''
        last_name = obj.employee.user.last_name or ''
        return f'{first_name} {last_name}'.strip() or obj.employee.user.email

    def get_download_url(self, obj):
        request = self.context.get('request')
        path = f'/api/documents/{obj.pk}/download/'
        return request.build_absolute_uri(path) if request else path

    def validate(self, attrs):
        if self.instance is None and not attrs.get('file'):
            raise serializers.ValidationError({'file': 'A file is required.'})
        return attrs

    def _attach_file_data(self, validated_data):
        uploaded_file = validated_data.pop('file', None)
        if uploaded_file:
            data = uploaded_file.read()
            validated_data['file_name'] = uploaded_file.name
            validated_data['content_type'] = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
            validated_data['size'] = getattr(uploaded_file, 'size', None) or len(data)
            validated_data['data'] = data
        return validated_data

    def create(self, validated_data):
        validated_data = self._attach_file_data(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._attach_file_data(validated_data)
        return super().update(instance, validated_data)
