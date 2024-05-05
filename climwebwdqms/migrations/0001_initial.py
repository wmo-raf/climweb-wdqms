# Generated by Django 4.2.11 on 2024-05-02 07:10

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Station',
            fields=[
                ('wigos_id', models.CharField(max_length=50, primary_key=True, serialize=False, verbose_name='Wigos ID')),
                ('name', models.CharField(max_length=50, verbose_name='Station name')),
                ('geom', django.contrib.gis.db.models.fields.PointField(srid=4326, verbose_name='Geometry')),
                ('in_oscar', models.BooleanField(verbose_name='In Oscar?')),
            ],
            options={
                'verbose_name': 'Station',
                'verbose_name_plural': 'Stations',
            },
        ),
        migrations.CreateModel(
            name='Observation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variable', models.CharField(max_length=50, verbose_name='Observation Variable')),
                ('received_rate', models.IntegerField(verbose_name='Percentage received')),
                ('received_date', models.DateTimeField(verbose_name='Date Time Received')),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='climwebwdqms.station')),
            ],
            options={
                'verbose_name': 'Observation',
                'verbose_name_plural': 'Observations',
            },
        ),
    ]