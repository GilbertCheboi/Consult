# Generated by Django 2.2.20 on 2021-10-15 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0011_did'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='casestatus',
            field=models.CharField(blank=True, default='Close', max_length=16, null=True, verbose_name='Case Status'),
        ),
    ]
