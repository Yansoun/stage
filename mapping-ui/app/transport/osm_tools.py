from geopy.geocoders import Nominatim
import requests

geolocator = Nominatim(user_agent="erp_env_project")

def geocode_address(address):
    location = geolocator.geocode(address)

    if location is None:
        raise Exception(f"Could not geocode address: {address}")

    return location.latitude, location.longitude
def get_distance_km(origin_lat, origin_lon, dest_lat, dest_lon):
    url = f"http://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"

    response = requests.get(url)
    data = response.json()

    if data["code"] != "Ok":
        raise Exception(f"OSRM Error: {data}")

    distance_meters = data["routes"][0]["distance"]

    return distance_meters / 1000