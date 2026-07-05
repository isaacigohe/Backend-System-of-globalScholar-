from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom manager for our User model. We override create_user and
    create_superuser so Django's management commands (createsuperuser,
    test fixtures) work correctly with our email-based auth.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.HOME_ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Central user model for GlobalScholar.

    Role breakdown:
      STUDENT       — applies to university programs abroad
      HOME_ADMIN    — staff at the student's home institution who approve docs
      HOST_COORD    — coordinator at the destination (host) university
    """

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        HOME_ADMIN = "HOME_ADMIN", "Home Admin"
        HOST_COORD = "HOST_COORD", "Host Coordinator"
        
    class StudentType(models.TextChoices):
        UNDERGRADUATE = "UNDERGRADUATE", "Undergraduate Student"
        POSTGRADUATE  = "POSTGRADUATE",  "Postgraduate Student"
        HIGH_SCHOOL   = "HIGH_SCHOOL",   "High School Student"
        INDEPENDENT   = "INDEPENDENT",   "Independent Learner"

    # ── Identity ──────────────────────────────────────────────────────────────
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    # ── Host Coordinator specific ────────────────────────────────────────────
    host_university = models.ForeignKey(
        'universities.University',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='host_coordinators',
        help_text="The university this coordinator manages (only for HOST_COORD role)."
    )

    # ── Student-specific fields ───────────────────────────────────────────────
    # These are nullable so HOME_ADMIN and HOST_COORD rows stay clean.
    # Business logic in serializers enforces them for STUDENT role.
    gpa = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Student's current GPA on a 4.0 scale.",
    )
    major = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Student's declared major at home institution.",
    )
    home_institution = models.CharField(
        max_length=300,
        null=True,
        blank=True,
        help_text="Name of the student's home university.",
    )
    enrollment_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Academic year the student enrolled (e.g. 2022).",
    )
    student_type = models.CharField(
        max_length=20,
        choices=StudentType.choices,
        null=True,
        blank=True,
        default=StudentType.UNDERGRADUATE,
        help_text="Type of student — determines which eligibility rules apply.",
    )

    # ── Account state ─────────────────────────────────────────────────────────
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "role"]

    class Meta:
        db_table = "gs_users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}> [{self.role}]"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    # ── Convenience role-check properties ─────────────────────────────────────
    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_home_admin(self):
        return self.role == self.Role.HOME_ADMIN

    @property
    def is_host_coordinator(self):
        return self.role == self.Role.HOST_COORD
    
    @property
    def is_high_school_student(self):
        return self.student_type == self.StudentType.HIGH_SCHOOL

    @property
    def is_independent_learner(self):
        return self.student_type == self.StudentType.INDEPENDENT

    @property
    def requires_gpa_check(self):
        # Only undergraduate and postgraduate students go through the GPA guardrail
        return self.student_type in [
            self.StudentType.UNDERGRADUATE,
            self.StudentType.POSTGRADUATE,
        ]