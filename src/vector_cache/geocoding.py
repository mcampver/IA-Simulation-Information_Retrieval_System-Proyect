import shelve
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# Caché simple en disco con shelve
_CACHE_DB = "data/geocode_cache.db"
_geolocator = Nominatim(user_agent="vectorcache")
_geocode = RateLimiter(_geolocator.geocode, min_delay_seconds=1)

def get_latlon(address: str) -> tuple[float, float]:
    """
    Devuelve (lat, lon) para una dirección de texto.
    Usa caché en disco para no repetir peticiones.
    """
    with shelve.open(_CACHE_DB) as db:
        if address in db:
            return db[address]
        loc = _geocode(address)
        if loc is None:
            raise ValueError(f"No pude geocodificar: {address}")
        coords = (loc.latitude, loc.longitude)
        db[address] = coords
        return coords
