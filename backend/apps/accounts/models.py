from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.text import slugify
from apps.core.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    current_organization = models.ForeignKey('Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='active_users')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.email


class Organization(TimeStampedModel):
    PLAN_CHOICES = (
        ('FREE', 'Free'),
        ('STARTER', 'Starter'),
        ('BUSINESS', 'Business'),
        ('ENTERPRISE', 'Enterprise'),
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='FREE')
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f'{base}-{counter}'
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Membership(TimeStampedModel):
    ROLE_OWNER = 'OWNER'
    ROLE_ADMIN = 'ADMIN'
    ROLE_HR = 'HR'
    ROLE_MANAGER = 'MANAGER'
    ROLE_EMPLOYEE = 'EMPLOYEE'
    ROLE_PAYROLL = 'PAYROLL'
    ROLE_IT = 'IT'
    ROLE_VIEWER = 'VIEWER'
    ROLE_CHOICES = (
        (ROLE_OWNER, 'Owner'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_HR, 'HR'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_EMPLOYEE, 'Employee'),
        (ROLE_PAYROLL, 'Payroll'),
        (ROLE_IT, 'IT / Asset Manager'),
        (ROLE_VIEWER, 'Viewer'),
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'user')

    def __str__(self):
        return f'{self.user.email} - {self.organization.name} - {self.role}'
