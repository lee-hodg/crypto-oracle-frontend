# Generated by Django 3.1.6 on 2021-02-16 01:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('predictor', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='stock',
            unique_together={('name', 'dt')},
        ),
    ]
