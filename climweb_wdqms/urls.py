from django.urls import path

from .views import (
    StationListView,
    SynopTransmissionView,
    MonthlyTransmissionView,
    YearlyTransmissionView,
    AverageMonthlyReceivedRateGeom
)

urlpatterns = [
    path('api/synop-transmission-rate/', SynopTransmissionView.as_view(), name='synop-transmission-rate'),
    path('api/monthly-transmission-rate/', MonthlyTransmissionView.as_view(), name='monthly-transmission-rate'),
    path('api/yearly-transmission-rate/', YearlyTransmissionView.as_view(), name='yearly-transmission-rate'),
    path('api/monthly-geom-transmission-rate/', AverageMonthlyReceivedRateGeom.as_view(), name='monthly-geom-transmission-rate'),
    path('api/stations/', StationListView.as_view(), name='station-list'),
]