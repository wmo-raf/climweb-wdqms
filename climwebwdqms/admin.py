from django.contrib import admin

from .models import Station, Observation
# Register your models here.
admin.site.register(Station)
admin.site.register(Observation)
