from geopy.geocoders import Nominatim
import time
#from geopy.extra.rate_limiter import RateLimiter
geolocator = Nominatim(user_agent='geopyProject')

def geo_worker(coordenates):
    i, row = coordenates
    time.sleep(1)
    location = geolocator.reverse(row['coord'],  timeout=None)
   
    address = location.raw['address'] 
    road = address['road'] if 'road' in address else 'N/A'
    town = address['house_number'] if 'house_number' in address else 'N/A'
    county = address['county'] if 'county' in address else 'N/A'
    neighbourhood = address['neighbourhood'] if 'neighbourhood' in address else 'N/A'

    return road, town, neighbourhood, county,
