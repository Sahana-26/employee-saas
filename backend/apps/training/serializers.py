from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from apps.hr.models import Employee
from .models import (
    TrainingAssessment,
    TrainingCertificate,
    TrainingCourse,
    TrainingEnrollment,
    TrainingMaterial,
    TrainingSubmission,
)


class TrainingCourseSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    material_count = serializers.IntegerField(read_only=True)
    enrollment_count = serializers.IntegerField(read_only=True)
    is_enrolled_by_me = serializers.SerializerMethodField()
    my_progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = TrainingCourse
        fields = [
            'id', 'organization', 'code', 'title', 'category', 'level', 'description', 'skills_covered',
            'duration_hours', 'is_mandatory', 'audience_roles', 'status', 'published_at', 'archived_at',
            'created_by', 'created_by_email', 'material_count', 'enrollment_count', 'is_enrolled_by_me',
            'my_progress_percent', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'published_at', 'archived_at', 'created_by', 'created_by_email',
            'material_count', 'enrollment_count', 'is_enrolled_by_me', 'my_progress_percent', 'created_at', 'updated_at',
        ]

    def get_is_enrolled_by_me(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        employee = Employee.objects.filter(organization=obj.organization, user=request.user).first()
        if not employee:
            return False
        return obj.enrollments.filter(employee=employee).exists()

    def get_my_progress_percent(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        employee = Employee.objects.filter(organization=obj.organization, user=request.user).first()
        if not employee:
            return None
        enrollment = obj.enrollments.filter(employee=employee).first()
        return enrollment.progress_percent if enrollment else None

    def validate_audience_roles(self, value):
        if value in [None, '']:
            return []
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError('Audience roles must be a JSON list.')
        if not isinstance(value, list):
            raise serializers.ValidationError('Audience roles must be a list.')
        return value


class TrainingMaterialSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    course_title = serializers.CharField(source='course.title', read_only=True)
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    download_url = serializers.SerializerMethodField()
    has_file = serializers.BooleanField(read_only=True)

    class Meta:
        model = TrainingMaterial
        fields = [
            'id', 'organization', 'course', 'course_title', 'title', 'material_type', 'external_url', 'notes',
            'file', 'file_name', 'content_type', 'file_size', 'download_url', 'has_file', 'uploaded_by',
            'uploaded_by_email', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'file_name', 'content_type', 'file_size', 'download_url', 'has_file',
            'uploaded_by', 'uploaded_by_email', 'created_at', 'updated_at',
        ]

    def get_download_url(self, obj):
        if not obj.file_data:
            return ''
        request = self.context.get('request')
        path = f'/api/training-materials/{obj.pk}/download/'
        return request.build_absolute_uri(path) if request else path

    def validate(self, attrs):
        request = self.context.get('request')
        course = attrs.get('course', getattr(self.instance, 'course', None))
        if request and course and course.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Course must belong to your organization.')
        if attrs.get('material_type') != TrainingMaterial.TYPE_LINK and self.instance is None and not attrs.get('file') and not attrs.get('external_url'):
            raise serializers.ValidationError({'file': 'Upload a file or provide an external URL.'})
        return attrs

    def _attach_file_data(self, validated_data):
        uploaded_file = validated_data.pop('file', None)
        if uploaded_file:
            data = uploaded_file.read()
            validated_data['file_name'] = uploaded_file.name
            validated_data['content_type'] = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
            validated_data['file_size'] = getattr(uploaded_file, 'size', None) or len(data)
            validated_data['file_data'] = data
        return validated_data

    def create(self, validated_data):
        validated_data = self._attach_file_data(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._attach_file_data(validated_data)
        return super().update(instance, validated_data)


class TrainingEnrollmentSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    assigned_by_email = serializers.EmailField(source='assigned_by.email', read_only=True)
    certificate_number = serializers.CharField(source='certificate.certificate_number', read_only=True)

    class Meta:
        model = TrainingEnrollment
        fields = [
            'id', 'organization', 'course', 'course_code', 'course_title', 'employee', 'employee_code',
            'employee_name', 'assigned_by', 'assigned_by_email', 'due_date', 'status', 'progress_percent',
            'started_at', 'completed_at', 'notes', 'certificate_number', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'assigned_by', 'assigned_by_email', 'status', 'started_at', 'completed_at',
            'certificate_number', 'created_at', 'updated_at',
        ]

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def validate(self, attrs):
        request = self.context.get('request')
        org_id = request.user.current_organization_id if request else None
        course = attrs.get('course', getattr(self.instance, 'course', None))
        employee = attrs.get('employee', getattr(self.instance, 'employee', None))
        progress = attrs.get('progress_percent', getattr(self.instance, 'progress_percent', 0))
        if course and org_id and course.organization_id != org_id:
            raise serializers.ValidationError('Course must belong to your organization.')
        if employee and org_id and employee.organization_id != org_id:
            raise serializers.ValidationError('Employee must belong to your organization.')
        if progress and progress > 100:
            raise serializers.ValidationError('Progress cannot be more than 100 percent.')
        return attrs


class TrainingAssessmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = TrainingAssessment
        fields = [
            'id', 'organization', 'course', 'course_title', 'title', 'instructions', 'max_score', 'passing_score',
            'questions', 'is_published', 'created_by', 'created_by_email', 'submission_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_by', 'created_by_email', 'submission_count', 'created_at', 'updated_at']

    def get_submission_count(self, obj):
        return obj.submissions.count()

    def validate(self, attrs):
        request = self.context.get('request')
        course = attrs.get('course', getattr(self.instance, 'course', None))
        if request and course and course.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Course must belong to your organization.')
        max_score = attrs.get('max_score', getattr(self.instance, 'max_score', Decimal('100')))
        passing_score = attrs.get('passing_score', getattr(self.instance, 'passing_score', Decimal('60')))
        if passing_score > max_score:
            raise serializers.ValidationError('Passing score cannot exceed max score.')
        return attrs


class TrainingSubmissionSerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(source='assessment.title', read_only=True)
    course_title = serializers.CharField(source='assessment.course.title', read_only=True)
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = TrainingSubmission
        fields = [
            'id', 'organization', 'assessment', 'assessment_title', 'course_title', 'employee', 'employee_code',
            'employee_name', 'enrollment', 'answers', 'score', 'status', 'feedback', 'submitted_at',
            'reviewed_by', 'reviewed_by_email', 'reviewed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'employee', 'enrollment', 'status', 'submitted_at', 'reviewed_by',
            'reviewed_by_email', 'reviewed_at', 'created_at', 'updated_at',
        ]

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def validate(self, attrs):
        request = self.context.get('request')
        assessment = attrs.get('assessment', getattr(self.instance, 'assessment', None))
        if request and assessment and assessment.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Assessment must belong to your organization.')
        return attrs


class TrainingSubmissionReviewSerializer(serializers.Serializer):
    score = serializers.DecimalField(max_digits=8, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)


class TrainingCertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    issued_by_email = serializers.EmailField(source='issued_by.email', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = TrainingCertificate
        fields = [
            'id', 'organization', 'certificate_number', 'employee', 'employee_code', 'employee_name', 'course',
            'course_title', 'enrollment', 'issued_at', 'issued_by', 'issued_by_email', 'download_url', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def get_download_url(self, obj):
        request = self.context.get('request')
        path = f'/api/training-certificates/{obj.pk}/download/'
        return request.build_absolute_uri(path) if request else path
