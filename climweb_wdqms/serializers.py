from rest_framework import serializers

from climweb_wdqms.models import Transmission, Station


class StationSerializer(serializers.ModelSerializer):
    geom = serializers.SerializerMethodField()

    class Meta:
        model = Station
        fields = ('wigos_id', 'name', 'geom', "in_oscar")

    def get_geom(self, obj):
        return obj.geom

class TransmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transmission
        fields = ["received_date", "station", "variable", "received_rate", "recieved", "expected"]

