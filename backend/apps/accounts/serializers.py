from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Organization, Membership


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'industry', 'plan', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'avatar', 'role', 'organization']

    def get_role(self, obj):
        org = obj.current_organization
        if not org:
            return None
        membership = obj.memberships.filter(organization=org, is_active=True).first()
        return membership.role if membership else None

    def get_organization(self, obj):
        if not obj.current_organization:
            return None
        return OrganizationSerializer(obj.current_organization).data


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(write_only=True, required=False)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'organization', 'user', 'user_email', 'role', 'is_active', 'created_at']
        read_only_fields = ['id', 'organization', 'user', 'created_at']

    def create(self, validated_data):
        request = self.context['request']
        email = validated_data.pop('user_email')
        user, _ = User.objects.get_or_create(email=email, defaults={'is_active': True})
        if not user.has_usable_password():
            user.set_unusable_password()
            user.save()
        return Membership.objects.create(organization=request.user.current_organization, user=user, **validated_data)


class RegisterOrganizationSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=180)
    industry = serializers.CharField(max_length=120, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    @transaction.atomic
    def create(self, validated_data):
        org = Organization.objects.create(
            name=validated_data['organization_name'],
            industry=validated_data.get('industry', ''),
            plan='FREE'
        )
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            current_organization=org,
        )
        Membership.objects.create(organization=org, user=user, role=Membership.ROLE_OWNER)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        if user.current_organization:
            token['organization_id'] = user.current_organization_id
            membership = user.memberships.filter(organization=user.current_organization, is_active=True).first()
            token['role'] = membership.role if membership else None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
