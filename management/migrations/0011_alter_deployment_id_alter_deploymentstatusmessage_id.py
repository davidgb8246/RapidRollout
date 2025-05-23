# Generated by Django 5.2.1 on 2025-05-21 15:50

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0010_rename_commit_uuid_deployment_commit_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deployment',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='deploymentstatusmessage',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]
