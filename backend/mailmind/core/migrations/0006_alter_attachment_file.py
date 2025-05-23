# Generated by Django 5.0.7 on 2025-04-25 21:13

import mailmind.core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_email_ai_processed_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attachment",
            name="file",
            field=models.FileField(
                upload_to=mailmind.core.models.attachment_upload_path
            ),
        ),
    ]
