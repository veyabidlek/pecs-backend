# Generated by Django 4.2.13 on 2024-10-11 07:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0007_alter_history_time_codes'),
    ]

    operations = [
        migrations.AddField(
            model_name='history',
            name='board',
            field=models.ForeignKey(default=False, on_delete=django.db.models.deletion.CASCADE, to='apps.board'),
        ),
        migrations.AlterField(
            model_name='codes',
            name='time',
            field=models.TimeField(default='12:56:41'),
        ),
        migrations.AlterField(
            model_name='history',
            name='time',
            field=models.TimeField(default='12:56:41'),
        ),
    ]
