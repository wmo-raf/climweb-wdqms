from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.functional import cached_property

class Station(models.Model):

    wigos_id = models.CharField(_("Wigos ID"), max_length=50, primary_key=True)
    name = models.CharField(_("Station name"), max_length=255)
    geom = models.PointField(_("Geometry"),)
    in_oscar = models.BooleanField(_("In Oscar?"),)

    class Meta:
        verbose_name = _("Station")
        verbose_name_plural = _("Stations")

    def __str__(self):
        return f'{self.name}-{self.wigos_id}'
    
    @cached_property
    def stations_api(self):
        return reverse("stations_api")

        
# Create your models here.
class Transmission(models.Model):

    station = models.ForeignKey("Station", on_delete=models.CASCADE)
    variable = models.CharField(_("Transmission Variable"), max_length=50 )
    received = models.IntegerField(_("Transmissions received"), null=True)
    expected = models.IntegerField(_("Transmissions expected"), null=True)
    received_rate = models.DecimalField(_("Transmission Rate"), max_digits=5, decimal_places=2)
    received_date = models.DateTimeField(_("Date Time Received"), auto_now=False, auto_now_add=False)

    class Meta:
        verbose_name = _("Transmission")
        verbose_name_plural = _("Transmissions")

    def __str__(self):
        return f'{self.station} - {self.variable} - {self.received_date}'
    


