# Generated by Django 3.2.13 on 2022-10-06 23:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0022_auto_20221007_0225'),
    ]

    operations = [
        migrations.AddField(
            model_name='clock',
            name='ip_address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='helpline.ipaddress'),
        ),
    ]
