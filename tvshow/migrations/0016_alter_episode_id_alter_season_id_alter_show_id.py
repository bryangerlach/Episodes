# Generated by Django 5.0.3 on 2024-11-22 00:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tvshow', '0015_alter_episode_date_watched'),
    ]

    operations = [
        migrations.AlterField(
            model_name='episode',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='season',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='show',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]