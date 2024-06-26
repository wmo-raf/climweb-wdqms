# Generated by Django 4.2.11 on 2024-05-12 00:08

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
                ('name', models.CharField(max_length=255, verbose_name='Station name')),
                ('geom', django.contrib.gis.db.models.fields.PointField(srid=4326, verbose_name='Geometry')),
                ('in_oscar', models.BooleanField(verbose_name='In Oscar?')),
            ],
            options={
                'verbose_name': 'Station',
                'verbose_name_plural': 'Stations',
            },
        ),
        migrations.CreateModel(
            name='Transmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variable', models.CharField(max_length=50, verbose_name='Transmission Variable')),
                ('received', models.IntegerField(null=True, verbose_name='Transmissions received')),
                ('expected', models.IntegerField(null=True, verbose_name='Transmissions expected')),
                ('received_rate', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Transmission Rate')),
                ('received_date', models.DateTimeField(verbose_name='Date Time Received')),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='climweb_wdqms.station')),
            ],
            options={
                'verbose_name': 'Transmission',
                'verbose_name_plural': 'Transmissions',
            },
        ),
    ]
