# Generated by Django 5.1.6 on 2025-03-30 16:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('word', '0007_blogpost'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
    ]
