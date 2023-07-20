# Generated by Django 2.2.25 on 2022-03-20 15:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0012_auto_20211015_1111'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='backend_manager_config',
            field=models.ForeignKey(blank=True, help_text='Backend Server', null=True, on_delete=django.db.models.deletion.SET_NULL, to='helpline.BackendServerManagerConfig'),
        ),
    ]
