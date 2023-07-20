# Generated by Django 2.2.18 on 2021-05-03 20:20

from django.db import migrations, models
import helpline.models


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0008_sipserverconfig_webrtc_gateway_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='backendservermanagerconfig',
            name='pbxapi_url',
            field=models.URLField(default=helpline.models.pbxapi_url_default),
        ),
    ]
