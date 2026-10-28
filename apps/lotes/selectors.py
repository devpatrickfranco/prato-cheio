from django.utils import timezone

from .geo import caixa_delimitadora, haversine_km
from .models import Lote


def lotes_na_vitrine(origem=None, raio_km=None):
    """Lotes disponíveis e dentro da validade, do que vence primeiro ao último.

    Com `origem` (lat, lon), cada lote recebe `distancia_km` até o
    estabelecimento (None se ele não tiver coordenadas). Com `origem` e
    `raio_km`, ficam apenas os lotes a no máximo `raio_km` de distância.
    """
    lotes = (
        Lote.objects
        .filter(status=Lote.Status.DISPONIVEL, data_validade__gte=timezone.localdate())
        .select_related('estabelecimento', 'categoria')
        .order_by('data_validade', 'retirada_inicio')
    )
    filtrar = origem is not None and raio_km is not None
    if filtrar:
        faixa_lat, faixa_lon = caixa_delimitadora(origem, raio_km)
        lotes = lotes.filter(
            estabelecimento__latitude__range=faixa_lat,
            estabelecimento__longitude__range=faixa_lon,
        )

    resultado = []
    for lote in lotes:
        destino = lote.estabelecimento.coordenadas
        lote.distancia_km = haversine_km(origem, destino) if origem and destino else None
        if filtrar and (lote.distancia_km is None or lote.distancia_km > raio_km):
            continue
        resultado.append(lote)
    return resultado
