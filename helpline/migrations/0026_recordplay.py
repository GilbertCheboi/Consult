# Generated by Django 3.2.13 on 2022-10-23 17:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('helpline', '0025_auto_20221021_0615'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecordPlay',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numeric_id', models.BigIntegerField(blank=True, null=True)),
                ('name', models.CharField(blank=True, max_length=50, null=True)),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Created on')),
                ('audio', models.BooleanField(default=False)),
                ('audio_codec', models.CharField(blank=True, max_length=10, null=True)),
                ('video', models.BooleanField(default=False)),
                ('video_codec', models.CharField(blank=True, max_length=10, null=True)),
                ('data', models.BooleanField(default=False)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
