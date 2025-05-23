# Generated by Django 4.2.20 on 2025-05-11 12:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("freelance", "0003_alter_freelanceproject_project_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="FreelanceGlobalConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "login_url",
                    models.URLField(default="https://www.freelance.de/login.php"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Freelance Global Config",
                "verbose_name_plural": "Freelance Global Configs",
            },
        ),
        migrations.RenameField(
            model_name="freelanceprovidercredential",
            old_name="link_1",
            new_name="link",
        ),
        migrations.RemoveField(
            model_name="freelanceprovidercredential",
            name="link_2",
        ),
        migrations.RemoveField(
            model_name="freelanceprovidercredential",
            name="link_3",
        ),
    ]
