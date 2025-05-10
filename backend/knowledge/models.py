from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import re

def validate_key_format(value):
    """Ensure the key only contains letters, numbers, and underscores."""
    if not re.match(r'^[a-zA-Z0-9_]+$', value):
        raise ValidationError(
            _('Key must only contain letters, numbers, and underscores (_).')
        )
    if not re.match(r'^[a-zA-Z]', value):
        raise ValidationError(
            _('Key must start with a letter.')
        )

class KnowledgeField(models.Model):
    """Stores a user-defined key-value pair for knowledge injection into prompts."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='knowledge_fields',
        verbose_name=_("User")
    )
    key = models.CharField(
        _("Key"), 
        max_length=100, 
        help_text=_("Identifier used in prompts like {key}. Only letters, numbers, underscores allowed. Must start with a letter."),
        validators=[validate_key_format]
    )
    value = models.TextField(
        _("Value"), 
        help_text=_("The content associated with the key.")
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Knowledge Field")
        verbose_name_plural = _("Knowledge Fields")
        ordering = ['key']
        constraints = [
            models.UniqueConstraint(fields=['user', 'key'], name='unique_user_key')
        ]

    def __str__(self):
        return f"{self.user.username} - {self.key}"
