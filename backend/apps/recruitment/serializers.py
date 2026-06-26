from django.db import transaction
from rest_framework import serializers
from apps.accounts.models import Membership, User
from apps.hr.models import Department, Employee
from .models import Candidate, InterviewRound, JobOpening, OfferLetter


class JobOpeningSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    hiring_manager_name = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    candidate_count = serializers.IntegerField(read_only=True)
    interview_count = serializers.SerializerMethodField()
    offer_count = serializers.SerializerMethodField()

    class Meta:
        model = JobOpening
        fields = [
            'id', 'organization', 'job_code', 'title', 'department', 'department_name', 'hiring_manager',
            'hiring_manager_name', 'employment_type', 'work_mode', 'location', 'openings_count',
            'min_experience', 'max_experience', 'salary_min', 'salary_max', 'description', 'requirements',
            'status', 'target_start_date', 'published_at', 'closed_at', 'created_by', 'created_by_email',
            'candidate_count', 'interview_count', 'offer_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'published_at', 'closed_at', 'created_by', 'created_by_email',
            'candidate_count', 'interview_count', 'offer_count', 'created_at', 'updated_at',
        ]

    def get_hiring_manager_name(self, obj):
        if not obj.hiring_manager:
            return ''
        return f'{obj.hiring_manager.user.first_name} {obj.hiring_manager.user.last_name}'.strip() or obj.hiring_manager.user.email

    def get_interview_count(self, obj):
        return obj.interviews.count()

    def get_offer_count(self, obj):
        return obj.offers.count()

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs
        org_id = request.user.current_organization_id
        department = attrs.get('department', getattr(self.instance, 'department', None))
        hiring_manager = attrs.get('hiring_manager', getattr(self.instance, 'hiring_manager', None))
        if department and department.organization_id != org_id:
            raise serializers.ValidationError('Department must belong to your organization.')
        if hiring_manager and hiring_manager.organization_id != org_id:
            raise serializers.ValidationError('Hiring manager must belong to your organization.')
        min_experience = attrs.get('min_experience', getattr(self.instance, 'min_experience', 0))
        max_experience = attrs.get('max_experience', getattr(self.instance, 'max_experience', 0))
        salary_min = attrs.get('salary_min', getattr(self.instance, 'salary_min', 0))
        salary_max = attrs.get('salary_max', getattr(self.instance, 'salary_max', 0))
        if max_experience and min_experience and max_experience < min_experience:
            raise serializers.ValidationError('Maximum experience cannot be less than minimum experience.')
        if salary_max and salary_min and salary_max < salary_min:
            raise serializers.ValidationError('Maximum salary cannot be less than minimum salary.')
        return attrs


class CandidateSerializer(serializers.ModelSerializer):
    resume = serializers.FileField(write_only=True, required=False)
    full_name = serializers.CharField(read_only=True)
    job_title = serializers.CharField(source='job_opening.title', read_only=True)
    job_code = serializers.CharField(source='job_opening.job_code', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    resume_download_url = serializers.SerializerMethodField()
    interview_count = serializers.SerializerMethodField()
    offer_count = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            'id', 'organization', 'job_opening', 'job_title', 'job_code', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'source', 'current_company', 'current_designation', 'experience_years',
            'current_ctc', 'expected_ctc', 'notice_period_days', 'skills', 'status', 'rejection_reason',
            'notes', 'resume', 'resume_file_name', 'resume_content_type', 'resume_size', 'resume_download_url',
            'created_by', 'created_by_email', 'interview_count', 'offer_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'rejection_reason', 'resume_file_name', 'resume_content_type',
            'resume_size', 'resume_download_url', 'created_by', 'created_by_email', 'interview_count',
            'offer_count', 'created_at', 'updated_at',
        ]

    def get_resume_download_url(self, obj):
        if not obj.resume_data:
            return ''
        request = self.context.get('request')
        path = f'/api/candidates/{obj.pk}/download-resume/'
        return request.build_absolute_uri(path) if request else path

    def get_interview_count(self, obj):
        return obj.interviews.count()

    def get_offer_count(self, obj):
        return obj.offers.count()

    def validate(self, attrs):
        request = self.context.get('request')
        job_opening = attrs.get('job_opening', getattr(self.instance, 'job_opening', None))
        if request and job_opening and job_opening.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Job opening must belong to your organization.')
        return attrs

    def _attach_resume(self, validated_data):
        uploaded_file = validated_data.pop('resume', None)
        if uploaded_file:
            data = uploaded_file.read()
            validated_data['resume_file_name'] = uploaded_file.name
            validated_data['resume_content_type'] = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
            validated_data['resume_size'] = getattr(uploaded_file, 'size', None) or len(data)
            validated_data['resume_data'] = data
        return validated_data

    def create(self, validated_data):
        validated_data = self._attach_resume(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._attach_resume(validated_data)
        return super().update(instance, validated_data)


class CandidateStatusSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class InterviewRoundSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.full_name', read_only=True)
    candidate_email = serializers.EmailField(source='candidate.email', read_only=True)
    job_title = serializers.CharField(source='job_opening.title', read_only=True)
    interviewer_name = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    completed_by_email = serializers.EmailField(source='completed_by.email', read_only=True)

    class Meta:
        model = InterviewRound
        fields = [
            'id', 'organization', 'candidate', 'candidate_name', 'candidate_email', 'job_opening', 'job_title',
            'round_type', 'interviewer', 'interviewer_name', 'scheduled_at', 'duration_minutes', 'mode',
            'meeting_link', 'location', 'status', 'result', 'rating', 'feedback', 'created_by',
            'created_by_email', 'completed_by', 'completed_by_email', 'completed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'result', 'rating', 'feedback', 'created_by', 'created_by_email',
            'completed_by', 'completed_by_email', 'completed_at', 'created_at', 'updated_at',
        ]

    def get_interviewer_name(self, obj):
        if not obj.interviewer:
            return ''
        return f'{obj.interviewer.user.first_name} {obj.interviewer.user.last_name}'.strip() or obj.interviewer.user.email

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs
        org_id = request.user.current_organization_id
        candidate = attrs.get('candidate', getattr(self.instance, 'candidate', None))
        job_opening = attrs.get('job_opening', getattr(self.instance, 'job_opening', None))
        interviewer = attrs.get('interviewer', getattr(self.instance, 'interviewer', None))
        if candidate and candidate.organization_id != org_id:
            raise serializers.ValidationError('Candidate must belong to your organization.')
        if job_opening and job_opening.organization_id != org_id:
            raise serializers.ValidationError('Job opening must belong to your organization.')
        if interviewer and interviewer.organization_id != org_id:
            raise serializers.ValidationError('Interviewer must belong to your organization.')
        return attrs


class InterviewCompleteSerializer(serializers.Serializer):
    result = serializers.ChoiceField(choices=InterviewRound.RESULT_CHOICES)
    rating = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=0, max_value=5, required=False)
    feedback = serializers.CharField(required=False, allow_blank=True)


class InterviewCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
    no_show = serializers.BooleanField(default=False, required=False)


class OfferLetterSerializer(serializers.ModelSerializer):
    document = serializers.FileField(write_only=True, required=False)
    candidate_name = serializers.CharField(source='candidate.full_name', read_only=True)
    candidate_email = serializers.EmailField(source='candidate.email', read_only=True)
    job_title = serializers.CharField(source='job_opening.title', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    converted_employee_code = serializers.CharField(source='converted_employee.employee_code', read_only=True)
    document_download_url = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = OfferLetter
        fields = [
            'id', 'organization', 'offer_number', 'candidate', 'candidate_name', 'candidate_email', 'job_opening',
            'job_title', 'department', 'department_name', 'offered_designation', 'joining_date', 'salary_basic',
            'ctc', 'valid_until', 'is_expired', 'status', 'notes', 'document', 'document_file_name',
            'document_content_type', 'document_size', 'document_download_url', 'sent_at', 'accepted_at',
            'rejected_at', 'converted_at', 'created_by', 'created_by_email', 'converted_employee',
            'converted_employee_code', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'document_file_name', 'document_content_type', 'document_size',
            'document_download_url', 'sent_at', 'accepted_at', 'rejected_at', 'converted_at', 'created_by',
            'created_by_email', 'converted_employee', 'converted_employee_code', 'is_expired', 'created_at', 'updated_at',
        ]

    def get_document_download_url(self, obj):
        if not obj.document_data:
            return ''
        request = self.context.get('request')
        path = f'/api/offers/{obj.pk}/download-document/'
        return request.build_absolute_uri(path) if request else path

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs
        org_id = request.user.current_organization_id
        candidate = attrs.get('candidate', getattr(self.instance, 'candidate', None))
        job_opening = attrs.get('job_opening', getattr(self.instance, 'job_opening', None))
        department = attrs.get('department', getattr(self.instance, 'department', None))
        if candidate and candidate.organization_id != org_id:
            raise serializers.ValidationError('Candidate must belong to your organization.')
        if job_opening and job_opening.organization_id != org_id:
            raise serializers.ValidationError('Job opening must belong to your organization.')
        if department and department.organization_id != org_id:
            raise serializers.ValidationError('Department must belong to your organization.')
        if candidate and job_opening and candidate.job_opening_id and candidate.job_opening_id != job_opening.id:
            raise serializers.ValidationError('Offer job opening should match the candidate job opening.')
        return attrs

    def _attach_document(self, validated_data):
        uploaded_file = validated_data.pop('document', None)
        if uploaded_file:
            data = uploaded_file.read()
            validated_data['document_file_name'] = uploaded_file.name
            validated_data['document_content_type'] = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
            validated_data['document_size'] = getattr(uploaded_file, 'size', None) or len(data)
            validated_data['document_data'] = data
        return validated_data

    def create(self, validated_data):
        validated_data = self._attach_document(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._attach_document(validated_data)
        return super().update(instance, validated_data)


class ConvertOfferSerializer(serializers.Serializer):
    employee_code = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=Membership.ROLE_CHOICES, default=Membership.ROLE_EMPLOYEE)
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=False, allow_null=True)
    designation = serializers.CharField(required=False, allow_blank=True)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    salary_basic = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    employment_type = serializers.ChoiceField(choices=Employee.EMPLOYMENT_TYPE_CHOICES, default='FULL_TIME')

    def validate(self, attrs):
        request = self.context['request']
        offer = self.context['offer']
        org = request.user.current_organization
        department = attrs.get('department') or offer.department
        if department and department.organization_id != org.id:
            raise serializers.ValidationError('Department must belong to your organization.')
        if Employee.objects.filter(organization=org, employee_code=attrs['employee_code']).exists():
            raise serializers.ValidationError({'employee_code': 'Employee code already exists.'})
        if User.objects.filter(email=offer.candidate.email).exists():
            raise serializers.ValidationError({'email': 'A user with this candidate email already exists.'})
        if offer.converted_employee_id:
            raise serializers.ValidationError('Offer is already converted to employee.')
        if offer.status != OfferLetter.STATUS_ACCEPTED:
            raise serializers.ValidationError('Only accepted offers can be converted into employees.')
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        request = self.context['request']
        offer = self.context['offer']
        candidate = offer.candidate
        org = request.user.current_organization
        department = self.validated_data.get('department') or offer.department
        designation = self.validated_data.get('designation') or offer.offered_designation
        salary_basic = self.validated_data.get('salary_basic', offer.salary_basic)
        date_of_joining = self.validated_data.get('date_of_joining') or offer.joining_date
        user = User.objects.create_user(
            email=candidate.email,
            password=self.validated_data['password'],
            first_name=candidate.first_name,
            last_name=candidate.last_name,
            phone=candidate.phone,
            current_organization=org,
            is_active=True,
        )
        Membership.objects.create(
            organization=org,
            user=user,
            role=self.validated_data.get('role', Membership.ROLE_EMPLOYEE),
            is_active=True,
        )
        employee = Employee.objects.create(
            organization=org,
            user=user,
            employee_code=self.validated_data['employee_code'],
            department=department,
            designation=designation,
            phone=candidate.phone,
            personal_email=candidate.email,
            date_of_joining=date_of_joining,
            employment_type=self.validated_data.get('employment_type', 'FULL_TIME'),
            status='ACTIVE',
            salary_basic=salary_basic,
        )
        offer.status = OfferLetter.STATUS_CONVERTED
        offer.converted_employee = employee
        from django.utils import timezone
        offer.converted_at = timezone.now()
        offer.save(update_fields=['status', 'converted_employee', 'converted_at', 'updated_at'])
        candidate.status = Candidate.STATUS_HIRED
        candidate.save(update_fields=['status', 'updated_at'])
        return employee
