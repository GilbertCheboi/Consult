# Generated by Django 3.2.13 on 2022-11-22 03:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0026_recordplay'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='managed',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]