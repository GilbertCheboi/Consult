# Generated by Django 2.2.18 on 2021-02-23 18:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('helpline', '0006_auto_20210218_1746'),
    ]

    operations = [
        migrations.AddField(
            model_name='clock',
            name='break_reason',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='helpline.Break'),
        ),
        migrations.AddField(
            model_name='clock',
            name='clock_in',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Clock in'),
        ),
        migrations.AddField(
            model_name='clock',
            name='clock_out',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Clock out'),
        ),
        migrations.AddField(
            model_name='clock',
            name='duration',
            field=models.DurationField(blank=True, null=True, verbose_name='Duration'),
        ),
        migrations.AlterField(
            model_name='break',
            name='status',
            field=models.CharField(choices=[('A', 'Active'), ('I', 'Inactive')], default='A', max_length=1),
        ),
    ]
