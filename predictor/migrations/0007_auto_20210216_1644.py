# Generated by Django 3.1.6 on 2021-02-16 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('predictor', '0006_auto_20210216_1544'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingsession',
            name='test_dates',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trainingsession',
            name='training_dates',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
