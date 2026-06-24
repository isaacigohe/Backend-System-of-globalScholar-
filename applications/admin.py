# applications/admin.py
# Registers Application, DocumentChecklist, and CreditTransferLog in admin.

from django.contrib import admin
from .models import Application, DocumentChecklist, CreditTransferLog


class DocumentChecklistInline(admin.TabularInline):
    # Shows all documents for an application directly inside the application page
    model        = DocumentChecklist
    extra        = 0
    readonly_fields = ('document_type', 'file_attachment', 'uploaded_at',
                       'verification_status', 'admin_comment', 'reviewed_by', 'reviewed_at')
    can_delete   = False


class CreditTransferInline(admin.TabularInline):
    # Shows all credit logs for an application directly inside the application page
    model        = CreditTransferLog
    extra        = 0
    readonly_fields = ('host_course_code', 'host_course_name', 'host_credits',
                       'transfer_status', 'submitted_by')
    can_delete   = False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display  = ('id', 'student', 'destination_university', 'status',
                     'gpa_at_submission', 'submitted_at', 'decision_at')
    list_filter   = ('status', 'destination_university__country')
    search_fields = ('student__email', 'student__first_name',
                     'destination_university__name')
    ordering      = ('-created_at',)
    readonly_fields = ('gpa_at_submission', 'submitted_at', 'reviewed_at',
                       'decision_at', 'created_at', 'updated_at')

    # Embeds documents and credit logs inside the application detail page
    inlines = [DocumentChecklistInline, CreditTransferInline]

    fieldsets = (
        ('Parties',    {'fields': ('student', 'destination_university', 'program', 'reviewed_by')}),
        ('Pipeline',   {'fields': ('status', 'rejection_reason', 'admin_notes')}),
        ('Snapshot',   {'fields': ('gpa_at_submission',)}),
        ('Timestamps', {'fields': ('submitted_at', 'reviewed_at', 'decision_at',
                                   'created_at', 'updated_at')}),
    )


@admin.register(DocumentChecklist)
class DocumentChecklistAdmin(admin.ModelAdmin):
    list_display  = ('id', 'application', 'document_type', 'verification_status',
                     'uploaded_at', 'reviewed_by', 'reviewed_at')
    list_filter   = ('verification_status', 'document_type', 'is_mandatory')
    search_fields = ('application__student__email', 'document_type')
    ordering      = ('-created_at',)
    readonly_fields = ('uploaded_at', 'reviewed_at', 'created_at', 'updated_at')


@admin.register(CreditTransferLog)
class CreditTransferLogAdmin(admin.ModelAdmin):
    list_display  = ('id', 'application', 'host_course_code', 'host_course_name',
                     'host_credits', 'transfer_status', 'submitted_by')
    list_filter   = ('transfer_status',)
    search_fields = ('host_course_code', 'host_course_name',
                     'application__student__email')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')