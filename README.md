# climweb-wdqms

Package to retrieve station transmissions from the [WIGOS Data Quality Monitoring System (WDQMS)](https://wdqms.wmo.int/) webtool. 
The WDQMS webtool is a resource developed by WMO to monitor the performance of all WIGOS observing components.

## Installation

```sh
pip install climweb-wdqms
```

Add to install apps

```py
installed_apps = [
  ...
  climweb_wdqms
]
```

## Usage

```sh
python manage.py wdqms_stats -var pressure
```

To retrieve data, arguements include:

**Mandatory**
- -var or --variable (Choose one. Accepted variables are e.g pressure,temperature, humidity, meridional_wind, zonal_wind)

**Optional**
- -s or --start_date (Start date of transmission. format YYYY-MM-DD. Defaults to 2023-01-01 if no data found, or uses the latest date for the specified variable)
- -e or --end_date (End date of transmission. format YYYY-MM-DD. Defaults to the last avaiable date on wdqms)
- -c or --centers (List of monitoring centers e.g DWD, ECMWF, JMA, NCEP. Defaults to all centers)
- -p or --periods (List of synoptic hours e.g 00, 06, 12, 18. Defaults to all periods)

## API Endpoints

**[GET] Fetch geojson of all stations**

```
api/stations/
```

---

**[GET] Fetch synop i.e (00, 06, 12, 18) data. (UTC timezone).** 

Supported_params include:
- station i.e the **wigos ID** of the station as registered in [OSCAR Surface](https://oscar.wmo.int/surface)
- frequency e.g **daily_synop, monthly_synop, yearly_synop**
- received_date in format **YYYY-MM-DD**
- variable e.g pressure, temperature, humidity, etc
  
```
api/synop-transmission-rate/
```

---

**[GET] Fetch monthly summary of transmission rates.**

Supported_params include:
- station i.e the **wigos ID** of the station as registered in [OSCAR Surface](https://oscar.wmo.int/surface)
- year in format **YYYY**
- variable e.g pressure, temperature, humidity, etc

```
api/monthly-transmission-rate/
```

---

**[GET] Fetch yearly summary of transmission rates.**

Supported_params include:
- station i.e the wigos ID of the station as registered in [OSCAR Surface](https://oscar.wmo.int/surface)
- variable e.g pressure, temperature, humidity, etc

```
api/yearly-transmission-rate/
```
---

**[GET] Fetch geojson of monthly transmission rates.**
Supported_params include:

- month in format **MM**
- year in format **YYYY**
- variable e.g pressure, temperature, humidity, etc

```
api/monthly-geom-transmission-rate/
```

## Demo

![wdqms-2](https://github.com/wmo-raf/climweb-wdqms/assets/28197485/47a37d61-7dc2-40be-a61f-ee2a7f3a6e47)
