# Generated by Django 3.2.13 on 2023-07-19 05:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendly', '0002_rename_token_accesstoken_access_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accesstoken',
            name='access_token',
            field=models.CharField(max_length=500),
        ),
    ]