from django.db import models


class University(models.Model):
    """
    Represents a destination (host) university that students can apply to.

    travel_advisory_level is populated automatically by our scraper utility
    (universities/scraper.py) and should never be edited manually in production.
    """

    class AdvisoryLevel(models.TextChoices):
        UNKNOWN = "UNKNOWN", "Unknown"
        NORMAL = "NORMAL", "Normal — No advisory"
        LEVEL_1 = "LEVEL_1", "Level 1 — Exercise Normal Precautions"
        LEVEL_2 = "LEVEL_2", "Level 2 — Exercise Increased Caution"
        LEVEL_3 = "LEVEL_3", "Level 3 — Reconsider Travel"
        LEVEL_4 = "LEVEL_4", "Level 4 — Do Not Travel"

    class Language(models.TextChoices):
        ENGLISH = "English", "English"
        FRENCH = "French", "French"
        GERMAN = "German", "German"
        SPANISH = "Spanish", "Spanish"
        MANDARIN = "Mandarin", "Mandarin"
        ARABIC = "Arabic", "Arabic"
        PORTUGUESE = "Portuguese", "Portuguese"
        OTHER = "Other", "Other"

    # ── Core identity ──────────────────────────────────────────────────────────
    name = models.CharField(max_length=300, unique=True)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True, default="")
    website = models.URLField(blank=True, default="")
    
    # ── Image ──────────────────────────────────────────────────────────────────
    image = models.ImageField(
        upload_to='universities/',
        null=True,
        blank=True,
        help_text="University logo or campus image"
    )

    # ── Academic requirements ──────────────────────────────────────────────────
    minimum_gpa = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        help_text="Minimum GPA (out of 4.0) required for application.",
    )
    primary_language = models.CharField(
        max_length=50,
        choices=Language.choices,
        default=Language.ENGLISH,
    )
    language_test_required = models.BooleanField(
        default=False,
        help_text="Whether an official language test (IELTS/TOEFL/DELF) is required.",
    )
    minimum_language_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum score on language proficiency test if required.",
    )

    # ── Capacity ───────────────────────────────────────────────────────────────
    max_international_students = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Annual intake cap for international students. Null = no published cap.",
    )

    # ── Travel safety (scraper-populated) ─────────────────────────────────────
    travel_advisory_level = models.CharField(
        max_length=20,
        choices=AdvisoryLevel.choices,
        default=AdvisoryLevel.UNKNOWN,
        help_text="Populated automatically by the travel safety scraper.",
    )
    advisory_last_updated = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last successful scraper run for this university.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gs_universities"
        verbose_name = "University"
        verbose_name_plural = "Universities"
        ordering = ["country", "name"]

    def __str__(self):
        return f"{self.name} ({self.country})"


class Program(models.Model):
    """
    A specific academic program offered at a University.
    Students apply to Programs, not Universities directly — though the
    Application model also holds a direct University FK for fast querying.
    """

    class DegreeLevel(models.TextChoices):
        BACHELOR = "BACHELOR", "Bachelor's"
        MASTER = "MASTER", "Master's"
        PHD = "PHD", "PhD"
        EXCHANGE = "EXCHANGE", "Exchange / Non-degree"
        DIPLOMA = "DIPLOMA", "Diploma"

    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name="programs",
    )
    name = models.CharField(max_length=300)
    degree_level = models.CharField(max_length=20, choices=DegreeLevel.choices)
    duration_semesters = models.PositiveSmallIntegerField(
        help_text="Length of the program in semesters."
    )
    tuition_per_semester_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    credits_transferable = models.BooleanField(
        default=True,
        help_text="Whether credits earned are eligible for transfer back to the home institution.",
    )
    application_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Next upcoming application deadline for this program.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gs_programs"
        verbose_name = "Program"
        verbose_name_plural = "Programs"
        unique_together = [["university", "name", "degree_level"]]
        ordering = ["university", "name"]

    def __str__(self):
        return f"{self.name} [{self.degree_level}] @ {self.university.name}"