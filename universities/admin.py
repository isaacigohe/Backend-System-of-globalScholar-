# universities/admin.py
# Registers University and Program models in Django admin.

from django.contrib import admin
from .models import University, Program


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display  = ('name', 'country', 'city', 'minimum_gpa', 'primary_language',
                     'travel_advisory_level', 'advisory_last_updated')
    list_filter   = ('country', 'primary_language', 'travel_advisory_level',
                     'language_test_required')
    search_fields = ('name', 'country', 'city')
    ordering      = ('country', 'name')

    fieldsets = (
        ('Identity',     {'fields': ('name', 'country', 'city', 'website')}),
        ('Requirements', {'fields': ('minimum_gpa', 'primary_language',
                                     'language_test_required', 'minimum_language_score',
                                     'max_international_students')}),
        ('Travel Safety',{'fields': ('travel_advisory_level', 'advisory_last_updated')}),
    )
    readonly_fields = ('advisory_last_updated',)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display  = ('name', 'university', 'degree_level', 'duration_semesters',
                     'tuition_per_semester_usd', 'application_deadline')
    list_filter   = ('degree_level', 'credits_transferable')
    search_fields = ('name', 'university__name')
    ordering      = ('university', 'name')