# Generated by Django 3.2.13 on 2023-02-15 04:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0027_service_managed'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='backend_manager_config',
            field=models.ForeignKey(blank=True, help_text='Backend Manager Config', null=True, on_delete=django.db.models.deletion.SET_NULL, to='helpline.backendservermanagerconfig'),
        ),
    ]
