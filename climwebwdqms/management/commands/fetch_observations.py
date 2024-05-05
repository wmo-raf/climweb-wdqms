import logging
import csv
from datetime import datetime, timedelta
from django.contrib.gis.geos import Point
from django.db import transaction, IntegrityError
from collections import defaultdict
import pandas as pd
import numpy as np

import requests
from django.core.management.base import BaseCommand
from climwebwdqms.models import Station, Observation

logger = logging.getLogger(__name__)

# Define the base URL for the WDQMS csv download
BASE_URL = "https://wdqms.wmo.int/wdqmsapi/v1/download/synop/six_hour/availability"

# params---> "date=2024-05-01&period=18&variable=pressure&centers=DWD,ECMWF,JMA,NCEP&baseline=OSCAR"

def download_transmission_rate_csv(date, period, variable, centers, baseline, country_code):


    params = {
        'date': date,
        'period': period,
        'variable': variable,
        'centers': ','.join(centers),
        'baseline': baseline
    }
    file_name = f"{date}_{period}_{variable}.csv"

    print(f"DOWNLOAD: Starting download of {file_name}")


    response = requests.get(BASE_URL, params=params)

    # Check if the request was successful
    if response.status_code == 200:

        with open(file_name, 'wb') as f:
            f.write(response.content)

        print(f"DOWNLOAD: {file_name} downloaded successfully.")
        
        # Load the CSV data into a DataFrame
        df = pd.read_csv(file_name)
        # Group by 'name' and select the row with the highest 'received rate'
        max_rate_indices = df.groupby('wigosid')['#received'].idxmax()
        df_filtered = df.loc[max_rate_indices]
        df_filtered = df_filtered[df_filtered['country code'] == country_code]

        df_filtered['received_rate'] = (df_filtered['#received'] / df_filtered['#expected']) * 100
        df_filtered.replace([np.inf, -np.inf], 0, inplace=True)

        return df_filtered

    else:
        print("Failed to retrieve data. Status code:", response.status_code)

def generate_date_range(start_date, end_date):
    dates = []
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    while current_date <= datetime.strptime(end_date, "%Y-%m-%d"):
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    return dates


def ingest_transmission_rates():
    start_date = "2024-01-01"
    end_date = "2024-05-01"
    dates = generate_date_range(start_date, end_date)
    periods = ["00", "06", "12", "18"]
    variable = "pressure"
    centers = ["DWD", "ECMWF", "JMA", "NCEP"]
    baseline = "OSCAR" 
    country_code = "KEN"

    for date in dates:
        for period in periods:
            trans_rates = download_transmission_rate_csv(date, period, variable, centers, baseline, country_code)

            print(f"INGEST: Starting data ingestion for {date}-{period}")

            # Create or update stations
            stations_to_create = []
            for _, row in trans_rates.iterrows():
                station_data = {
                    'wigos_id': row['wigosid'],
                    'name': row['name'],
                    'geom':Point(row['longitude'], row['latitude']),
                    'in_oscar':row['in OSCAR']
                }
                
                stations_to_create.append(Station(**station_data))


            # Bulk create new stations
            Station.objects.bulk_create(stations_to_create, ignore_conflicts=True)

            # Create or update observations
            observations_to_create = []
            for _, row in trans_rates.iterrows():

                if Observation.objects.filter(station=row['wigosid'], variable=row['variable'], received_date=datetime.strptime(row['date'],'%Y-%m-%d %H:%M:%S%z')).exists():
                    observation_data = {
                        'received_rate':row['received_rate'],
                    }
                    Observation.objects.filter(station=row['wigosid'], variable=row['variable'], received_date=datetime.strptime(row['date'],'%Y-%m-%d %H:%M:%S%z')).update(**observation_data)

                else:
                    station = Station.objects.get(wigos_id=row['wigosid'])
                    observations_to_create.append(Observation(
                        station=station,
                        variable=row['variable'],
                        received_rate=row['received_rate'],
                        received_date=datetime.strptime(row['date'],'%Y-%m-%d %H:%M:%S%z')
                    ))

            # Bulk create new observations
            Observation.objects.bulk_create(observations_to_create, ignore_conflicts=True)
            
            print(f"INGEST: Completed ingestion for {date}-{period}")


class Command(BaseCommand):
    help = ('')

    def handle(self, *args, **options):
        ingest_transmission_rates()

        


            

        
        




        