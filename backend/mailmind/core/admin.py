from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, EmailVerification, EmailAccount, Email, Attachment, AISuggestion, Contact, AIAction

# Import Django Q models
from django_q.models import Schedule, Success, Failure
from django_q.admin import TaskAdmin, ScheduleAdmin, FailAdmin

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'is_staff', 'is_active', 'is_email_verified')
    list_filter = ('is_staff', 'is_active', 'is_email_verified')
    search_fields = ('email',)
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_email_verified', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')

@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'user', 'provider', 'is_active')
    list_filter = ('provider', 'is_active')
    search_fields = ('name', 'email', 'user__email')

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'short_summary', 'from_address', 'sent_at', 'received_at', 'is_read', 'is_flagged', 'ai_processed')
    list_filter = ('is_read', 'is_flagged', 'ai_processed', 'folder_name', 'account')
    search_fields = ('subject', 'from_address', 'body_text', 'short_summary', 'medium_summary', 'message_id', 'uid')
    date_hierarchy = 'sent_at'
    list_select_related = ('account',)

    fieldsets = (
        (None, {
            'fields': ('account', 'subject', 'from_address', 'from_name')
        }),
        ('AI Summaries', {
            'fields': ('short_summary', 'medium_summary'),
        }),
        ('Content', {
            'fields': ('body_text', 'body_html', 'markdown_body'),
            'classes': ('collapse',),
        }),
        ('Recipients', {
            'fields': ('to_contacts', 'cc_contacts', 'bcc_contacts', 'reply_to_contacts'),
            'classes': ('collapse',),
        }),
        ('Metadata & Status', {
            'fields': (
                'message_id', 'uid', 'folder_name', 'conversation_id', 
                'sent_at', 'received_at', 'date_str',
                'is_read', 'is_flagged', 'is_replied', 
                'is_deleted_on_server', 'is_draft',
                'ai_processed', 'ai_processed_at', 'embedding_generated',
                'size_rfc822', 'size',
                'created_at', 'updated_at'
            )
        }),
         ('Headers', {
            'fields': ('headers',),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = (
        'account', 'message_id', 'uid', 'folder_name', 'conversation_id', 
        'sent_at', 'received_at', 'date_str', 
        'size_rfc822', 'size',
        'created_at', 'updated_at', 'headers', 
        'is_read', 'is_flagged', 'is_replied', 'is_deleted_on_server', 'is_draft',
        'to_contacts', 'cc_contacts', 'bcc_contacts', 'reply_to_contacts', 'from_contact',
        'ai_processed', 'ai_processed_at', 'embedding_generated',
        'short_summary', 'medium_summary',
        'markdown_body',
    )
    
    filter_horizontal = ('to_contacts', 'cc_contacts', 'bcc_contacts', 'reply_to_contacts')

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'content_type', 'size', 'created_at')
    search_fields = ('filename', 'content_type')

@admin.register(AISuggestion)
class AISuggestionAdmin(admin.ModelAdmin):
    list_display = ('type', 'title', 'status', 'confidence_score', 'created_at')
    list_filter = ('type', 'status')
    search_fields = ('title', 'content')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'organization', 'interaction_count')
    search_fields = ('name', 'email', 'organization')
    list_filter = ('organization',)

@admin.register(AIAction)
class AIActionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    filter_horizontal = ("prompts",)

# Explicitly register Django Q models if they are missing (Cluster especially)
# Note: This might cause duplicate registration warnings if they *are* registered by default.
# Try removing specific lines if you see warnings after adding this.
if not admin.site.is_registered(Schedule):
    admin.site.register(Schedule, ScheduleAdmin)
if not admin.site.is_registered(Failure):
    admin.site.register(Failure, FailAdmin) 