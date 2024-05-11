from django.shortcuts import render
from rest_framework.generics import ListAPIView
from climwebwdqms.models import Transmission, Station
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from climwebwdqms.serializers import TransmissionSerializer, StationSerializer
from datetime import date, timedelta, datetime
from dateutil import parser
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models.functions import TruncMonth
from django.db.models import Count
from django.db.models.functions import ExtractHour,ExtractMonth,ExtractYear
from django.db.models import Avg

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
        queryset = Transmission.objects.all()

        # query parameters 
        station = request.query_params.get('station', None)
        frequency = request.query_params.get('frequency', None)
        received_date = request.query_params.get('received_date', queryset.order_by('received_date').values_list('received_date').last()[0].strftime("%Y-%m-%dT%H:%M:%SZ"))
        
        variable = request.query_params.get('variable', 'pressure')
        frequency = request.query_params.get('frequency', None)

        result = []

        if station:
            queryset = queryset.filter(station = station)

        if received_date:
            received_date = datetime.strptime(f"{received_date}", "%Y-%m-%dT%H:%M:%SZ")

            # check the frequencies 
            if frequency == 'monthly_synop':
                queryset = queryset.filter(received_date__month = received_date.month, variable=variable).order_by('received_date__hour')
            
            elif frequency == 'daily_synop':
                queryset = queryset.filter(received_date__day=received_date.day, variable=variable).order_by('received_date__hour')
            elif frequency == 'yearly_synop':
                queryset = queryset.filter(received_date__year = received_date.year, variable=variable).order_by('received_date__hour')

        # Extract the hour from the received_date and annotate the queryset
        queryset = queryset.annotate(
            synop_hour=ExtractHour('received_date')
        )

        # Aggregate the queryset to calculate the average received_rate for each synoptic hour
        queryset = queryset.values('synop_hour').annotate(
            avg_received_rate=Avg('received_rate')
        )

        # Format the result
        result = [
            {
                'synop_hour': str(hour).zfill(2),  # Format hour to have leading zero if needed
                'avg_received_rate': round(avg_rate, 0) if avg_rate else None  # Round to 2 decimal places
            }
            for hour, avg_rate in queryset.values_list('synop_hour', 'avg_received_rate')
        ] 
            
        # Return response
        return Response(result)


class MonthlyTransmissionView(APIView):

    def get(self, request):

        queryset = Transmission.objects.all()
        result = []

        latest_year =  queryset.values_list('received_date__year').order_by('received_date__year').last()

        # query params 
        station = request.query_params.get('station', None)
        year = request.query_params.get('year', latest_year[0] if len(latest_year) else None)
        variable = request.query_params.get('variable', 'pressure')

        if station:
            queryset = queryset.filter(station = station)

        # Extract the month from the received_date and annotate the queryset
        queryset = queryset.filter(variable=variable, received_date__year=year).annotate(
            month=ExtractMonth('received_date')
        )

        # Aggregate the queryset to calculate the average received_rate for each month
        monthly_averages = queryset.values('month').order_by('received_date__month').annotate(
            avg_received_rate=Avg('received_rate')
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
                'avg_received_rate': round(avg_rate, 2) if avg_rate else None  # Round to 2 decimal places
            }
            for month, avg_rate in monthly_averages.values_list('month', 'avg_received_rate')
        ]

        return Response(result)


class YearlyTransmissionView(APIView):

    def get(self, request):

        queryset = Transmission.objects.all()
        result = []

        # query params 
        station = request.query_params.get('station', None)
        variable = request.query_params.get('variable', 'pressure')

        if station:
            queryset = queryset.filter(station = station)

        # Extract the month from the received_date and annotate the queryset
        queryset = queryset.annotate(
            year=ExtractYear('received_date')
        )

        # Aggregate the queryset to calculate the average received_rate for each month
        yearly_averages = queryset.values('year').order_by('received_date__year').annotate(
            avg_received_rate=Avg('received_rate')
        )

        # Format the result
        result = [
            {
                'year': year,
                'avg_received_rate': round(avg_rate, 2) if avg_rate else None  # Round to 2 decimal places
            }
            for year, avg_rate in yearly_averages.values_list('year', 'avg_received_rate')
        ]

        return Response(result)




        









        return Response(result)




