"""Distâncias geográficas pela fórmula de Haversine."""
from math import asin, cos, degrees, radians, sin, sqrt

RAIO_TERRA_KM = 6371.0088  # raio médio da Terra (IUGG)


def haversine_km(origem, destino):
    """Distância em km, sobre a superfície da Terra, entre dois pontos (lat, lon).

    d = 2R · asin(√(sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)))
    """
    lat1, lon1 = origem
    lat2, lon2 = destino
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * RAIO_TERRA_KM * asin(min(1.0, sqrt(a)))


def caixa_delimitadora(origem, raio_km):
    """Faixas (lat_min, lat_max), (lon_min, lon_max) que contêm o círculo de `raio_km`.

    Serve como pré-filtro barato no banco antes do cálculo exato de Haversine.
    """
    lat, lon = origem
    angulo = raio_km / RAIO_TERRA_KM
    dlat = degrees(angulo)
    cos_lat = cos(radians(lat))
    dlon = 180.0 if cos_lat <= sin(angulo) else degrees(asin(sin(angulo) / cos_lat))
    return (lat - dlat, lat + dlat), (lon - dlon, lon + dlon)
