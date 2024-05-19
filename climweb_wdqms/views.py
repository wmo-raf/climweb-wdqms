from django.shortcuts import render
import pytz
import json

from rest_framework.generics import ListAPIView
from climweb_wdqms.models import Transmission, Station
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from climweb_wdqms.serializers import StationSerializer
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models.functions import ExtractHour,ExtractMonth,ExtractYear
from django.db.models import Avg, Func, F
from django.db.models.functions import TruncMonth
from django.utils.timezone import utc




def validate_params(query_params, supported_params):
    # Check for unsupported parameters
    error_message = None
    unsupported_params = [param for param in query_params.keys() if param not in supported_params]
    
    # If there are unsupported parameters, return an error response
    if unsupported_params:
        error_message = {'error': f'Unsupported parameter(s): {", ".join(unsupported_params)}. Only Supports {", ".join(supported_params)}'}
        # return Response(error_message, status=400)  # Return a 400 Bad Request response
    

    # Check if the 'param' parameter is present in the request
    for q in supported_params:
        if q not in query_params and q != 'station':
            error_message = {'error': f'Parameter "{q}" is required.'}
            # return Response(error_message, status=400)  # Return a 400 Bad Request response


    return error_message

class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
    

class StationListView(ListAPIView):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    permission_classes = [IsAuthenticated | ReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        wigos_id = self.request.query_params.get('wigos_id')
        if wigos_id:
            queryset = queryset.filter(wigos_id=wigos_id)
        return queryset
    
# Create your views here.
class SynopTransmissionView(APIView):
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["received_date", "station", "variable"]
    permission_classes = [IsAuthenticated | ReadOnly]

    def get(self, request):
        
        queryset = Transmission.objects.filter(received_date__year__gte = 2023)
        supported_params = ['station', 'frequency', 'received_date', 'variable']
        query_params = request.query_params
        
        validate = validate_params(query_params, supported_params)

        if validate:
            return Response(validate, status=400)  # Return a 400 Bad Request response

        # query parameters 
        station = request.query_params.get('station', None)
        frequency = request.query_params.get('frequency', None)
        received_date = request.query_params.get('received_date', queryset.order_by('received_date').values_list('received_date').last()[0].strftime("%Y-%m-%dT%H:%M:%SZ"))
        variable = request.query_params.get('variable', 'pressure')

        result = []

        if station is not None:
            queryset = queryset.filter(station = station)

        if received_date:
            received_date = datetime.strptime(f"{received_date}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)

            # check the frequencies 
            if frequency == 'monthly_synop':
                queryset = queryset.filter(received_date__year = received_date.year, received_date__month = received_date.month, variable=variable).order_by('received_date__hour')
            
            elif frequency == 'daily_synop':
                queryset = queryset.filter(received_date__date=received_date.date(), variable=variable).order_by('received_date__hour')
            elif frequency == 'yearly_synop':
                queryset = queryset.filter(received_date__year = received_date.year, variable=variable).order_by('received_date__hour')

        # Extract the hour from the received_date and annotate the queryset
        queryset = queryset.annotate(
            synop_hour=ExtractHour('received_date', tzinfo=utc)
        )

        # Aggregate the queryset to calculate the average received_rate for each synoptic hour
        queryset = queryset.values('synop_hour').annotate(
            avg_received_rate=Avg('received_rate'),
            avg_received=Avg('received'),
            avg_expected=Avg('expected'),
        )

        # Format the result
        result = [
            {
                'synop_hour': str(hour).zfill(2),  # Format hour to have leading zero if needed
                'avg_received_rate': round(avg_rate, 0), # Round to 0 decimal places
                'avg_received': round(avg_received, 0),  # Round to 0 decimal places
                'avg_expected': round(avg_expected, 0)  # Round to 0 decimal places
            }
            for hour, avg_rate, avg_received, avg_expected in queryset.values_list('synop_hour', 'avg_received_rate','avg_received', 'avg_expected' )
        ] 
            
        # Return response
        return Response(result)


class MonthlyTransmissionView(APIView):

    def get(self, request):

        queryset = Transmission.objects.filter(received_date__year__gte = 2023)
        result = []

        latest_year =  queryset.values_list('received_date__year').order_by('received_date__year').last()
        supported_params = ['station', 'year', 'variable']

        validate = validate_params(request.query_params, supported_params)

        if validate:
            return Response(validate, status=400)  # Return a 400 Bad Request response
        
        # query params 
        station = request.query_params.get('station', None)
        year = request.query_params.get('year', latest_year[0] if len(latest_year) else None)
        variable = request.query_params.get('variable', 'pressure')

        if station is not None:
            queryset = queryset.filter(station = station)

        # Extract the month from the received_date and annotate the queryset
        queryset = queryset.filter(variable=variable, received_date__year=year).annotate(
            month=ExtractMonth('received_date')
        )

        # Aggregate the queryset to calculate the average received_rate for each month
        monthly_averages = queryset.values('month').order_by('received_date__month').annotate(
            avg_received_rate=Avg('received_rate'),
            avg_received=Avg('received'),
            avg_expected=Avg('expected'),
        )

        # Map month numbers to month names
        MONTH_NAMES = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        # Format the result
        result = [
            {
                'month': MONTH_NAMES[month],
                'avg_received_rate': round(avg_rate, 0),  # Round to 0 decimal places
                'avg_received': round(avg_received, 0),  # Round to 0 decimal places
                'avg_expected': round(avg_expected, 0)  # Round to 0 decimal places
            }
            for month, avg_rate, avg_received, avg_expected in monthly_averages.values_list('month', 'avg_received_rate','avg_received', 'avg_expected')
        ]

        return Response(result)


class YearlyTransmissionView(APIView):

    def get(self, request):

        queryset = Transmission.objects.filter(received_date__year__gte = 2023)
        result = []

        supported_params = ['station', 'variable']

        validate = validate_params(request.query_params, supported_params)

        if validate:
            return Response(validate, status=400)  # Return a 400 Bad Request response

        # query params 
        station = request.query_params.get('station', None)
        variable = request.query_params.get('variable', 'pressure')
        

        if station is not None:
            queryset = queryset.filter(station = station)

        queryset = queryset.filter(variable=variable)

        # Extract the month from the received_date and annotate the queryset
        queryset = queryset.annotate(
            year=ExtractYear('received_date')
        )

        # Aggregate the queryset to calculate the average received_rate for each month
        yearly_averages = queryset.values('year').order_by('received_date__year').annotate(
            avg_received_rate=Avg('received_rate'),
            avg_received=Avg('received'),
            avg_expected=Avg('expected'),
        )

        # Format the result
        result = [
            {
                'year': year,
                'avg_received_rate': round(avg_rate, 0),  # Round to 0 decimal places
                'avg_received': round(avg_received, 0), # Round to 0 decimal places
                'avg_expected': round(avg_expected, 0)  # Round to 0 decimal places
            }
            for year, avg_rate, avg_received, avg_expected in yearly_averages.values_list('year', 'avg_received_rate','avg_received', 'avg_expected')
        ]

        return Response(result)



class AverageMonthlyReceivedRateGeom(APIView):
    def get(self, request):
        month = request.query_params.get('month', None)
        year = request.query_params.get('year', None)
        variable = request.query_params.get('variable', None)

        # Aggregate data by month and calculate average received rate
        monthly_data = Transmission.objects.filter(received_date__month=month,
            received_date__year=year, variable=variable
        ).annotate(
            month=TruncMonth('received_date')
        ).values(
            'month','station__name', 'variable', 'station__wigos_id'
        ).annotate(
            average_received_rate=Avg('received_rate'),
            station_geometry=F('station__geom'),  # Access the geometry field

        )

        # Convert queryset to list of dictionaries
        monthly_data_list = list(monthly_data)

        # Create GeoJSON-like structure
        feature_collection = {
            "type": "FeatureCollection",
            "features": []
        }

        for data in monthly_data_list:
            # Convert Decimal to float for JSON serialization
            average_received_rate = float(data['average_received_rate']) if data['average_received_rate'] is not None else None

            geometry = json.loads(data['station_geometry'].geojson)

            feature = {
                "type": "Feature",
                "properties": {
                    "name": data['station__name'],
                    "wigos_id": data['station__wigos_id'],
                    "month": data['month'].strftime('%Y-%m'),
                    "variable": data['variable'],
                    "average_received_rate": average_received_rate
                },
                "geometry": geometry
            }
            feature_collection["features"].append(feature)

        return Response(feature_collection)
