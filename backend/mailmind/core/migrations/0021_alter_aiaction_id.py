# Generated by Django 4.2.20 on 2025-05-04 16:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_aiaction"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aiaction",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
