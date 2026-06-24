# users/admin.py
# Registers the custom User model in Django admin panel.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Columns shown in the user list table
    list_display  = ('email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter   = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)

    # Fields shown when viewing/editing a single user
    fieldsets = (
        ('Identity',  {'fields': ('email', 'password')}),
        ('Personal',  {'fields': ('first_name', 'last_name', 'role')}),
        ('Student Info', {'fields': ('gpa', 'major', 'home_institution', 'enrollment_year')}),
        ('Permissions',  {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Dates',     {'fields': ('date_joined', 'last_login')}),
    )
    readonly_fields = ('date_joined', 'last_login')

    # Fields shown when creating a new user from admin
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )

    # Django expects username field — we use email instead
    USERNAME_FIELD = 'email'