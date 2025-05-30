# Generated by Django 5.2.1 on 2025-05-24 15:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0017_alter_privatefile_file_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='privatefile',
            name='file_type',
            field=models.CharField(choices=[('DEFAULT', 'Default File type'), ('ENV', 'ENV File type'), ('AFTER_START_SCRIPT', 'After Start Script File type')], default='DEFAULT', help_text='Type of the private file', max_length=20),
        ),
    ]
