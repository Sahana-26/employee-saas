from django.db import transaction
from rest_framework import serializers
from apps.accounts.permissions import HR_ROLES, MANAGER_ROLES, get_role
from apps.hr.models import Employee
from .models import GeneratedLetter, LetterAudit, LetterTemplate
from .rendering import DEFAULT_VARIABLES, render_letter


class LetterTemplateSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = LetterTemplate
        fields = [
            'id', 'organization', 'code', 'name', 'category', 'version', 'description', 'content',
            'available_variables', 'requires_approval', 'is_active', 'created_by', 'created_by_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'created_by', 'created_by_email', 'created_at', 'updated_at']

    def validate_available_variables(self, value):
        if value in [None, '']:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Available variables must be a list.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        role = get_role(request.user) if request else None
        if role not in HR_ROLES:
            raise serializers.ValidationError('Only HR/Admin/Owner can manage letter templates.')
        if not attrs.get('available_variables') and self.instance is None:
            attrs['available_variables'] = DEFAULT_VARIABLES
        return attrs


class LetterRenderPreviewSerializer(serializers.Serializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    custom_variables = serializers.JSONField(required=False)

    def validate_employee(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Employee must belong to the current organization.')
        return value


class GeneratedLetterSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_email = serializers.EmailField(source='employee.user.email', read_only=True)
    employee_name = serializers.SerializerMethodField()
    template_code = serializers.CharField(source='template.code', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    generated_by_email = serializers.EmailField(source='generated_by.email', read_only=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True)
    signed_by_email = serializers.EmailField(source='signed_by.email', read_only=True)
    issued_by_email = serializers.EmailField(source='issued_by.email', read_only=True)
    can_download = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedLetter
        fields = [
            'id', 'organization', 'employee', 'employee_code', 'employee_email', 'employee_name',
            'template', 'template_code', 'template_name', 'letter_number', 'title', 'category',
            'custom_variables', 'rendered_content', 'document_filename', 'document_content_type',
            'document_size', 'status', 'generated_by', 'generated_by_email', 'generated_at',
            'approved_by', 'approved_by_email', 'approved_at', 'rejected_by', 'rejected_at',
            'rejection_reason', 'signed_by', 'signed_by_email', 'signed_at', 'issued_by',
            'issued_by_email', 'issued_at', 'remarks', 'can_download', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'employee_code', 'employee_email', 'employee_name', 'template_code',
            'template_name', 'rendered_content', 'document_filename', 'document_content_type',
            'document_size', 'status', 'generated_by', 'generated_by_email', 'generated_at',
            'approved_by', 'approved_by_email', 'approved_at', 'rejected_by', 'rejected_at',
            'rejection_reason', 'signed_by', 'signed_by_email', 'signed_at', 'issued_by',
            'issued_by_email', 'issued_at', 'can_download', 'created_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        user = obj.employee.user
        return f'{user.first_name} {user.last_name}'.strip() or user.email

    def get_can_download(self, obj):
        return bool(obj.document_data and obj.status in [GeneratedLetter.STATUS_APPROVED, GeneratedLetter.STATUS_SIGNED, GeneratedLetter.STATUS_ISSUED])

    def validate_employee(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Employee must belong to the current organization.')
        return value

    def validate_template(self, value):
        request = self.context.get('request')
        if value and request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Template must belong to the current organization.')
        if value and not value.is_active:
            raise serializers.ValidationError('Template is archived/inactive.')
        return value

    def validate_custom_variables(self, value):
        if value in [None, '']:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('Custom variables must be a JSON object.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        role = get_role(request.user) if request else None
        if self.instance is None and role not in HR_ROLES:
            raise serializers.ValidationError('Only HR/Admin/Owner can create letters.')
        employee = attrs.get('employee') or getattr(self.instance, 'employee', None)
        template = attrs.get('template') or getattr(self.instance, 'template', None)
        if employee and template and employee.organization_id != template.organization_id:
            raise serializers.ValidationError('Employee and template must belong to the same organization.')
        if template:
            attrs.setdefault('category', template.category)
            attrs.setdefault('title', template.name)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        organization = request.user.current_organization
        if not validated_data.get('letter_number'):
            prefix = validated_data.get('category') or 'LETTER'
            next_no = GeneratedLetter.objects.filter(organization=organization).count() + 1
            validated_data['letter_number'] = f'{prefix}-{next_no:05d}'
        letter = GeneratedLetter.objects.create(
            organization=organization,
            generated_by=request.user,
            **validated_data,
        )
        template = letter.template
        if template:
            content = render_letter(template, letter.employee, letter.custom_variables)
            letter.set_generated_document(content)
            if not template.requires_approval:
                letter.status = GeneratedLetter.STATUS_APPROVED
                letter.approved_by = request.user
            letter.save()
        LetterAudit.objects.create(organization=organization, letter=letter, action='CREATED', actor=request.user)
        return letter

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get('request')
        if instance.status in [GeneratedLetter.STATUS_SIGNED, GeneratedLetter.STATUS_ISSUED, GeneratedLetter.STATUS_CANCELLED]:
            raise serializers.ValidationError('Signed, issued, or cancelled letters cannot be edited.')
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if instance.template:
            content = render_letter(instance.template, instance.employee, instance.custom_variables)
            instance.set_generated_document(content)
        instance.save()
        LetterAudit.objects.create(organization=instance.organization, letter=instance, action='UPDATED', actor=request.user)
        return instance


class LetterActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class LetterAuditSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)

    class Meta:
        model = LetterAudit
        fields = ['id', 'organization', 'letter', 'action', 'actor', 'actor_email', 'note', 'created_at']
        read_only_fields = fields
