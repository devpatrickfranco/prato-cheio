"""Geocodificação de endereço/CEP (latitude e longitude) pelo Nominatim, do OpenStreetMap.

Só é chamada no cadastro e na edição do estabelecimento. Qualquer falha (sem rede, sem resultado,
resposta inesperada) devolve None: o cadastro segue sem coordenadas e o usuário aparece sem
distância na vitrine. Desative com DJANGO_GEOCODIFICACAO=False.
Política de uso do serviço: https://operations.osmfoundation.org/policies/nominatim/
"""
import json
import logging
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

URL = 'https://nominatim.openstreetmap.org/search'
TIMEOUT_S = 5


def _buscar(parametros):
    consulta = urlencode({**parametros, 'format': 'jsonv2', 'limit': 1, 'countrycodes': 'br'})
    requisicao = Request(f'{URL}?{consulta}', headers={'User-Agent': settings.GEOCODIFICACAO_USER_AGENT})
    with urlopen(requisicao, timeout=TIMEOUT_S) as resposta:  # noqa: S310 - URL fixa (https)
        resultados = json.load(resposta)
    if not resultados:
        return None
    return Decimal(resultados[0]['lat']).quantize(Decimal('0.000001')), Decimal(resultados[0]['lon']).quantize(Decimal('0.000001'))


def geocodificar(cidade='', uf='', cep='', logradouro='', numero='', bairro=''):
    """Devolve (latitude, longitude) como Decimal, ou None se não for possível."""
    if not settings.GEOCODIFICACAO_ATIVA:
        return None
    tentativas = []
    if logradouro and cidade:
        rua = f'{numero} {logradouro}'.strip()
        tentativas.append({'street': rua, 'city': cidade, 'state': uf, 'postalcode': cep})
        tentativas.append({'street': rua, 'city': cidade, 'state': uf})
    if cep:
        tentativas.append({'postalcode': cep, 'city': cidade, 'state': uf})
    if cidade:
        tentativas.append({'city': cidade, 'state': uf})
    for parametros in tentativas:
        parametros = {chave: valor for chave, valor in parametros.items() if valor}
        try:
            coordenadas = _buscar(parametros)
        except (OSError, ValueError, KeyError, ArithmeticError) as erro:
            logger.warning('Geocodificação falhou (%s): %s', parametros, erro)
            return None
        if coordenadas:
            return coordenadas
    return None
