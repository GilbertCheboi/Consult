# Generated by Django 3.2.13 on 2023-07-19 05:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('calendly', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='accesstoken',
            old_name='token',
            new_name='access_token',
        ),
    ]