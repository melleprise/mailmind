from django.contrib import admin
from .models import PromptTemplate

@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'model_name', 'updated_at')
    list_filter = ('provider',)
    search_fields = ('name', 'description', 'template', 'model_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('AI Configuration', {
            'fields': ('provider', 'model_name')
        }),
        ('Template', {
            'fields': ('template',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',) # Initially collapsed
        }),
    )
