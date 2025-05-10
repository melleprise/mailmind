from django.db import models
from django.utils.translation import gettext_lazy as _

class PromptTemplate(models.Model):
    """Model to store AI prompt templates with provider and model details."""

    class ProviderChoices(models.TextChoices):
        OPENAI = 'openai', _('OpenAI')
        GOOGLE_GEMINI = 'google_gemini', _('Google Gemini')
        GROQ = 'groq', _('Groq')
        # Add other providers as needed

    name = models.SlugField(
        _("Name/Slug"), 
        max_length=100, 
        unique=True, 
        help_text=_("Unique identifier for the prompt (e.g., 'email_correction', 'suggestion_subject').")
    )
    description = models.TextField(
        _("Description"), 
        blank=True, 
        help_text=_("Brief description of what the prompt is used for.")
    )
    prompt = models.TextField(
        _("Prompt Content"), 
        help_text=_("The prompt template itself. Use placeholders like {context} or {email_body}.")
    )
    provider = models.CharField(
        _("AI Provider"), 
        max_length=50, 
        choices=ProviderChoices.choices, 
        default=ProviderChoices.GROQ, # Default to Groq for now
        help_text=_("The AI provider to use for this prompt.")
    )
    # Consider making model_name nullable or having a default based on provider?
    model_name = models.CharField(
        _("Model Name"), 
        max_length=100, 
        help_text=_("Specific model name from the provider (e.g., 'gpt-4-turbo', 'gemini-1.5-pro-latest', 'llama3-70b-8192').")
    )
    # Allow null for fixtures, remove auto fields
    created_at = models.DateTimeField(_("Created At"), null=True, blank=True)
    updated_at = models.DateTimeField(_("Updated At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Prompt Template")
        verbose_name_plural = _("Prompt Templates")
        ordering = ['name'] # Order alphabetically by name

    def __str__(self):
        return self.name
