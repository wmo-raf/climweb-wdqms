from django.contrib import admin

from .models import Station, Transmission


# Register your models here.

class TransmissionModelAdmin(admin.ModelAdmin):
    list_filter = ('variable', 'received_date')
    search_fields = [ 'station__name', 'received_date']
    list_display = ('station', 'received_date', 'variable', 'received_rate')



admin.site.register(Station)
admin.site.register(Transmission,TransmissionModelAdmin)


