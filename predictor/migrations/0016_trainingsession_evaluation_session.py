# Generated by Django 3.1.6 on 2021-02-19 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('predictor', '0015_stockprediction_actual'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingsession',
            name='evaluation_session',
            field=models.BooleanField(default=True),
        ),
    ]
