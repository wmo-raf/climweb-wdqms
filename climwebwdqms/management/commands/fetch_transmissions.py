import logging
import csv
import os
import re
from datetime import datetime, timedelta
from django.contrib.gis.geos import Point
import pandas as pd
import numpy as np

import requests
from django.core.management.base import BaseCommand
from climwebwdqms.models import Station, Transmission
from adminboundarymanager.models import Country

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
    file_name = os.path.join("tmp",f"{date}_{period}_{variable}.csv")

    print(f"DOWNLOAD: Starting download of {file_name}")


    response = requests.get(BASE_URL, params=params)

    # Check if the request was successful
    if response.status_code == 200:

        # Check if the directory already exists
        if not os.path.exists("tmp"):
            # Create the directory
            os.makedirs("tmp")

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

        os.remove(file_name)
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


def ingest_transmission_rates(start_date, end_date,variable, periods, centers, country_code):
    # start_date = "2024-01-01" # TODO: USER DEFINED
    # end_date = "2024-05-01" # TODO: USER DEFINED
    dates = generate_date_range(start_date, end_date)
    # periods = ["00", "06", "12", "18"] # TODO: USER DEFINED
    # variable = "pressure" # TODO: USER DEFINED
    # centers = ["DWD", "ECMWF", "JMA", "NCEP"] # TODO: USER DEFINED
    baseline = "OSCAR" 
    # country_code = "KEN" # TODO: USER DEFINED

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

            # Create or update transmissions
            transmissions_to_create = []
            for _, row in trans_rates.iterrows():

                if Transmission.objects.filter(station=row['wigosid'], variable=row['variable'], received_date=datetime.strptime(row['date'],'%Y-%m-%d %H:%M:%S%z')).exists():
                    transmission_data = {
                        'received_rate':row['received_rate'],
                    }
                    Transmission.objects.filter(station=row['wigosid'], variable=row['variable'], received_date=datetime.strptime(row['date'],'%Y-%m-%d %H:%M:%S%z')).update(**transmission_data)

                else:
                    station = Station.objects.get(wigos_id=row['wigosid'])
                    transmissions_to_create.append(Transmission(
                        station=station,
                        variable=row['variable'],
                        received_rate=row['received_rate'],
                        received_date=datetime.strptime(row['date'],'%Y-%m-%d %H:%M:%S%z')
                    ))

            # Bulk create new transmissions
            Transmission.objects.bulk_create(transmissions_to_create, ignore_conflicts=True)
            
            print(f"INGEST: Completed ingestion for {date}-{period}")



class Command(BaseCommand):
    help = ('Fetch Country level transmission rate from WDQMS')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument('-s', '--start_date', type=str, help='Start date of transmission. format YYYY-MM-DD') 
        parser.add_argument('-e', '--end_date', type=str, help='End date of transmission. format YYYY-MM-DD') 
        parser.add_argument('-var', '--variable', type=str, help='Accepted variables one of pressure,temperature, humidity, meridional_wind, zonal_wind') 
        parser.add_argument('-p', '--periods', nargs='+', type=str, help='List of synoptic hours e.g 00, 06, 12, 18') 
        parser.add_argument('-c', '--centers', nargs='+', type=str, help='List of monitoring centers e.g DWD, ECMWF, JMA, NCEP') 

        # Arguments are not added here since they will be parsed manually
        return

    def handle(self, *args, **kwargs):

        start_date = kwargs['start_date'] if kwargs['start_date'] is not None else self.stderr.write(self.style.ERROR(f"Missing start_date (-s) arguement. Accepts YYYY-MM-DD"))
        end_date = kwargs['end_date'] if kwargs['end_date'] is not None else self.stderr.write(self.style.ERROR(f"Missing end_date (-e) arguement. Accepts YYYY-MM-DD"))
        periods = kwargs['periods'] if kwargs['periods'] is not None else self.stderr.write(self.style.ERROR(f"Missing period (-p) arguement. Accepts 00, 06, 12, 18"))
        centers = kwargs['centers'] if kwargs['periods'] is not None else self.stderr.write(self.style.ERROR(f"Missing centers (-c) arguement. Accepts DWD, ECMWF, JMA, NCEP"))
        variable = kwargs['variable'].lower() if kwargs['periods'] is not None else self.stderr.write(self.style.ERROR(f"Missing centers (-var) arguement. Accepts one of  pressure,temperature, humidity, meridional_wind, zonal_wind"))

        variables_ls = ['pressure', 'temperature', 'humidity', 'meridional_wind' , 'zonal_wind']
        period_ls = ["00", "06", "12", "18"]
        center_ls = ["DWD", "ECMWF", "JMA", "NCEP"]

        # Regular expression to match YYYY-MM-DD format
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

        # Parsing the arguments manually
        if start_date:
            if not date_pattern.match(start_date):
                self.stderr.write(self.style.ERROR(f"Invalid format for 'start_date'. Use YYYY-MM-DD format."))
                return  # Exit the command

        if end_date:  
            if not date_pattern.match(end_date):
                self.stderr.write(self.style.ERROR(f"Invalid format for 'end_date'. Use YYYY-MM-DD format."))
                return  # Exit the command

        if variable:
            if variable not in variables_ls:
                self.stderr.write(self.style.ERROR(f"Allowed variables include pressure,temperature, humidity, meridional_wind, zonal_wind"))
                return  # Exit the command

            # Split the value by comma and append to list_arg
        print(periods)
        if periods:
            for period in periods:
                if period not in period_ls:
                    self.stderr.write(self.style.ERROR(f"'{period}' is not a valid option. Choices are 00 06 12 18"))
                    return  # Exit the command
            
        if centers:
            for center in centers:
                if center.upper() not in center_ls:
                    self.stderr.write(self.style.ERROR(f"'{center}' is not a valid option. Choices are DWD ECMWF JMA NCEP"))
                    return  # Exit the command


        if start_date and end_date and variable and centers and periods:
            for country in Country.objects.all():
                # loop through all countries in boundary manager for data fetching and ingestion
                self.stdout.write(f"FETCH: Requesting data for {country.country.name}")

                ingest_transmission_rates(start_date, end_date, variable, periods, centers, country.country.alpha3)
        
        # else:
        #     self.stderr.write(self.style.ERROR("Missing arguements for start_date, end_date, centers, variables, periods"))
        #     return

        


            

        
        




        