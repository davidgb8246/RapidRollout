# Generated by Django 5.2.1 on 2025-05-24 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0014_project_initialized'),
    ]

    operations = [
        migrations.AddField(
            model_name='privatefile',
            name='fileperms',
            field=models.CharField(default='600', max_length=3),
        ),
    ]
