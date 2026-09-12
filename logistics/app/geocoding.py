from __future__ import annotations

import requests

_geocode_cache: dict[str, tuple[float, float]] = {}

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'


def geocode_location(location: str) -> tuple[float, float] | None:
    if not location:
        return None

    key = location.strip().lower()
    if key in _geocode_cache:
        return _geocode_cache[key]

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={'q': location, 'format': 'json', 'limit': 1, 'countrycodes': 'in'},
            headers={'User-Agent': 'FarmDirect-FARMOVA-SIH-Project'},
            timeout=5,
        )
        response.raise_for_status()
        results = response.json()
    except requests.RequestException:
        return None

    if not results:
        return None

    coords = (float(results[0]['lat']), float(results[0]['lon']))
    _geocode_cache[key] = coords
    return coords
