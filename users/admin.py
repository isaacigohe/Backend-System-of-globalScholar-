from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'host_university', 'is_active')
    list_filter = ('role', 'is_active', 'host_university')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)  # Changed from 'username' to 'email'
    
    fieldsets = UserAdmin.fieldsets + (
        ('Role & University', {
            'fields': ('role', 'host_university', 'student_type'),
        }),
        ('Student Info', {
            'fields': ('gpa', 'major', 'home_institution', 'enrollment_year'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & University', {
            'fields': ('role', 'host_university', 'student_type'),
        }),
        ('Student Info', {
            'fields': ('gpa', 'major', 'home_institution', 'enrollment_year'),
        }),
    )