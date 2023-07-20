# Generated by Django 2.2.25 on 2022-06-01 19:40

from django.db import migrations
import helpline.models


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0015_hotdesk_primary'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sipserverconfig',
            name='webrtc_gateway_url',
            field=helpline.models.WebRTCURLField(default=helpline.models.webrtc_gateway_url_default),
        ),
    ]
