# Generated by Django 3.1.6 on 2021-02-23 15:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('predictor', '0016_trainingsession_evaluation_session'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='trainingsession',
            unique_together={('name', 'start_date', 'end_date', 'window_length', 'output_size', 'evaluation_session', 'neurons', 'shuffle_buffer_size', 'training_size', 'epochs', 'batch_size', 'dropout', 'optimizer', 'loss', 'activation_func')},
        ),
    ]
