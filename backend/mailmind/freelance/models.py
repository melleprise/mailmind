from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from cryptography.fernet import Fernet, InvalidToken
from mailmind.core.models import get_api_credential_encryption_key

User = get_user_model()

class FreelanceProject(models.Model):
    """Model für Freelance.de Projekte."""
    
    project_id = models.TextField(null=False, blank=False, unique=True)
    title = models.TextField(null=False, blank=False)
    company = models.TextField(null=False, blank=False)
    end_date = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    remote = models.BooleanField(default=False)
    last_updated = models.TextField(null=True, blank=True)
    skills = models.JSONField(default=list)
    url = models.TextField(null=False, blank=False)
    applications = models.IntegerField(null=True, blank=True)
    description = models.TextField(default="", blank=True)
    provider = models.TextField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'freelance_projects'
        unique_together = [['project_id', 'provider']]
        
    def __str__(self):
        return f"{self.title} - {self.company}" 

class FreelanceProviderCredential(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='freelance_credentials')
    username = models.CharField(max_length=255)
    password_encrypted = models.TextField()
    link_1 = models.TextField()
    link_2 = models.TextField()
    link_3 = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'username')
        verbose_name = "Freelance Provider Credential"
        verbose_name_plural = "Freelance Provider Credentials"
        ordering = ['user', 'username']

    def set_password(self, plain_password):
        key = get_api_credential_encryption_key()
        f = Fernet(key)
        self.password_encrypted = f.encrypt(plain_password.encode()).decode()

    def get_password(self):
        key = get_api_credential_encryption_key()
        f = Fernet(key)
        return f.decrypt(self.password_encrypted.encode()).decode() 