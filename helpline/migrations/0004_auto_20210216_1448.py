# Generated by Django 2.2.18 on 2021-02-16 14:48

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0003_service_disposition_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='disposition_choices',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=50), blank=True, null=True, size=None),
        ),
    ]