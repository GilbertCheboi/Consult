# Generated by Django 2.2.18 on 2021-05-03 21:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0009_backendservermanagerconfig_pbxapi_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='backendservermanagerconfig',
            name='pbxapi_password',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='backendservermanagerconfig',
            name='pbxapi_user',
            field=models.CharField(blank=True, max_length=12, null=True),
        ),
    ]
