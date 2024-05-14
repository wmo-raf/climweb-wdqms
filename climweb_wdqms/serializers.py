from rest_framework import serializers

from climweb_wdqms.models import Transmission, Station


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        # fields = ('wigos_id', 'name', "in_oscar", "geom")
        fields = "__all__"

    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [instance.geom.x, instance.geom.y]
            },
            'properties': {}
        }
        # Set all other fields as properties
        for field in representation:
            if field != 'geom':
                feature['properties'][field] = representation[field]
        return feature
        return representation

class TransmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transmission
        fields = ["received_date", "station", "variable", "received_rate", "recieved", "expected"]

