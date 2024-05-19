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
from climweb_wdqms.models import Station, Transmission
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
       
        df_filtered = df[df['country code'] == country_code]

        # Assuming df_filtered is your DataFrame
        df_filtered = df_filtered.copy()
        df_filtered['received_rate'] = (df_filtered['#received'] / df_filtered['#expected']) * 100
         # Group by 'name' and select the row with the highest 'received rate'
        max_rate_indices = df_filtered.groupby('wigosid')['received_rate'].idxmax()
        df_filtered = df_filtered.loc[max_rate_indices]
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


def ingest_transmission_rates(start_date, end_date, variable, periods, centers, country_code):
    dates = generate_date_range(start_date, end_date)
    baseline = "OSCAR" 

    print(f"INGEST: Ingesting {variable.upper()}...")
    variable = variable.lower()

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
                        'received':row['#received'],
                        'expected':row['#expected'],
                    }
                    Transmission.objects.filter(station=row['wigosid'], variable=row['variable'], received_date=datetime.strptime(row['date'],'%Y-%m-%d %H:%M:%S%z')).update(**transmission_data)

                else:
                    station = Station.objects.get(wigos_id=row['wigosid'])
                    transmissions_to_create.append(Transmission(
                        station=station,
                        variable=row['variable'],
                        received_rate=row['received_rate'],
                        received=row['#received'],
                        expected=row['#expected'],
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
        parser.add_argument('-var', '--variable', type=str, help='Accepted variables are e.g pressure,temperature, humidity, meridional_wind, zonal_wind') 
        parser.add_argument('-p', '--periods', nargs='+', type=str, help='List of synoptic hours e.g 00, 06, 12, 18') 
        parser.add_argument('-c', '--centers', nargs='+', type=str, help='List of monitoring centers e.g DWD, ECMWF, JMA, NCEP') 

        # Arguments are not added here since they will be parsed manually
        return

    def handle(self, *args, **kwargs):

        transmissions = Transmission.objects.all()
        yesterday = datetime.now().date() - timedelta(days=1)


        latest_date = None
        end_date = kwargs['end_date'] if kwargs['end_date'] is not None else yesterday.strftime("%Y-%m-%d")
        periods = kwargs['periods'] if kwargs['periods'] is not None else ["00", "06", "12", "18"]
        centers = kwargs['centers'] if kwargs['centers'] is not None else ["DWD", "ECMWF", "JMA", "NCEP"]
        variable = kwargs['variable'] if kwargs['variable'] is not None else ['pressure', 'temperature', 'humidity', 'meridional_wind' , 'zonal_wind']

        variables_ls = ['pressure', 'temperature', 'humidity', 'meridional_wind' , 'zonal_wind']
        period_ls = ["00", "06", "12", "18"]
        center_ls = ["DWD", "ECMWF", "JMA", "NCEP"]


        # Regular expression to match YYYY-MM-DD format
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

        if variable is not None:
            if variable not in variables_ls:
                self.stderr.write(self.style.ERROR(f"Accepeted variables include pressure,temperature, humidity, meridional_wind, zonal_wind"))
                return  # Exit the command
            else:
                # check latest date for variable
                latest_date = transmissions.filter(variable=variable).values_list('received_date__date').order_by('received_date__date').last()

     
        if kwargs['start_date'] is not None:
            # check first cli params
            start_date = kwargs['start_date']
        elif latest_date:
            # check latest date in db 
            start_date = latest_date[0].strftime("%Y-%m-%d")
        else:
            # use earliest date in wdqms. usually means the db is empty 
            start_date = "2023-01-01" 

        # Parsing the arguments manually
        if start_date is not None:
            if not date_pattern.match(start_date):
                self.stderr.write(self.style.ERROR(f"Invalid format for 'start_date'. Use YYYY-MM-DD format."))
                return  # Exit the command

        if end_date is not None:  
            if not date_pattern.match(end_date):
                self.stderr.write(self.style.ERROR(f"Invalid format for 'end_date'. Use YYYY-MM-DD format."))
                return  # Exit the command
            
        if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
            self.stderr.write(self.style.ERROR(f"'End date' cannot come earlier than 'Start date'"))
            return  # Exit the command


               # Split the value by comma and append to list_arg
        if periods is not None:
            for period in periods:
                if period not in period_ls:
                    self.stderr.write(self.style.ERROR(f"'{period}' is not a valid option. Choices are 00 06 12 18"))
                    return  # Exit the command
            
        if centers is not None:
            for center in centers:
                if center.upper() not in center_ls:
                    self.stderr.write(self.style.ERROR(f"'{center}' is not a valid option. Choices are DWD ECMWF JMA NCEP"))
                    return  # Exit the command
                
            

        if start_date is not None and end_date is not None and variable is not None and centers is not None and periods is not None:
            for country in Country.objects.all():
                if Country.objects.count() > 0:
                    # loop through all countries in boundary manager for data fetching and ingestion
                    self.stdout.write(f"FETCH: Requesting data for {country.country.name}")

                    ingest_transmission_rates(start_date, end_date, variable, periods, centers, country.country.alpha3)
                else:
                    self.stderr.write(self.style.ERROR(f"Please select atleast one country in admin boundary settings first"))


        


            

        
        




        