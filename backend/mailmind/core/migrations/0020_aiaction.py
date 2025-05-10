from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('prompt_templates', '0001_initial'),
        ('core', '0017_email_flags_alter_email_bcc_contacts_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('prompts', models.ManyToManyField(related_name='actions', to='prompt_templates.PromptTemplate')),
            ],
            options={
                'ordering': ['sort_order', 'name'],
            },
        ),
    ] 