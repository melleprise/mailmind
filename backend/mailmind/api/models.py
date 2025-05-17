from django.db import models
from django.conf import settings

class Draft(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.ForeignKey('core.Email', on_delete=models.CASCADE)
    subject = models.TextField(blank=True, default='')
    body = models.TextField(blank=True, default='')
    selected_suggestion_index = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'email')
        verbose_name = 'Draft'
        verbose_name_plural = 'Drafts'

    def __str__(self):
        return f"Draft for {self.email} by {self.user}" 