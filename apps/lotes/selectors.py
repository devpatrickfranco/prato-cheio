import unicodedata

from django.utils import timezone

from .geo import caixa_delimitadora, haversine_km
from .models import Categoria, Lote


def _normalizar(texto):
    """Minúsculas e sem acentos: 'Pão' casa com 'pao'."""
    sem_acento = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    return sem_acento.casefold().strip()


def _vitrine(tipo_perfil):
    agora = timezone.now()
    return (
        Lote.objects
        .filter(
            status=Lote.Status.DISPONIVEL,
            modalidade__in=Lote.MODALIDADES_POR_PERFIL[tipo_perfil],
            data_validade__gte=timezone.localdate(agora),
            retirada_fim__gt=agora,
        )
        .select_related('estabelecimento', 'categoria', 'alimento')
        .order_by('data_validade', 'retirada_inicio')
    )


def lotes_na_vitrine(tipo_perfil, origem=None, raio_km=None, busca='', categoria_id=None, bairro=''):
    """Lotes disponíveis e dentro da validade, do que vence primeiro ao último.

    `tipo_perfil` define as modalidades visíveis: doações só aparecem para ONGs.
    Com `origem` (lat, lon), cada lote recebe `distancia_km` até o
    estabelecimento (None se ele não tiver coordenadas). Com `origem` e
    `raio_km`, ficam apenas os lotes a no máximo `raio_km` de distância.
    `busca` procura (sem diferenciar acentos/maiúsculas) na descrição, no alimento, na
    categoria e no estabelecimento; `categoria_id` e `bairro` restringem a lista.
    """
    lotes = _vitrine(tipo_perfil)
    if categoria_id:
        lotes = lotes.filter(categoria_id=categoria_id)
    if bairro:
        lotes = lotes.filter(estabelecimento__bairro=bairro)
    filtrar = origem is not None and raio_km is not None
    if filtrar:
        faixa_lat, faixa_lon = caixa_delimitadora(origem, raio_km)
        lotes = lotes.filter(
            estabelecimento__latitude__range=faixa_lat,
            estabelecimento__longitude__range=faixa_lon,
        )

    termo = _normalizar(busca)
    resultado = []
    for lote in lotes:
        if termo:
            alvo = _normalizar(' '.join([
                lote.descricao, lote.categoria.nome, lote.estabelecimento.razao_social,
                lote.alimento.descricao if lote.alimento_id else '',
            ]))
            if termo not in alvo:
                continue
        destino = lote.estabelecimento.coordenadas
        lote.distancia_km = haversine_km(origem, destino) if origem and destino else None
        if filtrar and (lote.distancia_km is None or lote.distancia_km > raio_km):
            continue
        resultado.append(lote)
    return resultado


def opcoes_de_filtro(tipo_perfil):
    """Categorias e bairros que têm lotes na vitrine do perfil agora (para os selects de filtro)."""
    lotes = _vitrine(tipo_perfil)
    categorias = Categoria.objects.filter(pk__in=lotes.values('categoria_id')).order_by('nome')
    bairros = sorted(set(lotes.values_list('estabelecimento__bairro', flat=True)))
    return categorias, bairros
