# Generated by Django 5.0.3 on 2024-11-18 18:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tvshow', '0013_show_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='episode',
            name='episodeImage',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
    ]
