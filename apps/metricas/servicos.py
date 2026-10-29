"""Cálculo das métricas de impacto a partir das retiradas confirmadas.

Só conta lote `retirado`, ou seja, com `Reserva` confirmada pelo doador:
- kg salvos = soma de `Lote.peso_kg`;
- CO₂ evitado = soma de `Lote.co2_evitado_kg`;
- refeições estimadas = kg salvos / 0,4 kg por refeição.
O doador vê as retiradas do seu estabelecimento; consumidor e ONG, as próprias retiradas.
"""
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from apps.lotes.models import Reserva

KG_POR_REFEICAO = Decimal('0.4')
MESES_NO_GRAFICO = 6
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']


@dataclass
class Retirada:
    reserva: Reserva
    quando: object
    kg: Decimal
    co2_kg: Decimal

    @property
    def lote(self):
        return self.reserva.lote


@dataclass
class Totais:
    kg: Decimal = Decimal('0')
    co2_kg: Decimal = Decimal('0')
    retiradas: int = 0

    @property
    def refeicoes(self):
        return (self.kg / KG_POR_REFEICAO).quantize(Decimal('1'))

    def somar(self, retirada):
        self.kg += retirada.kg
        self.co2_kg += retirada.co2_kg
        self.retiradas += 1


def retiradas_do_usuario(usuario):
    """Retiradas confirmadas, da mais recente para a mais antiga."""
    if usuario.tipo_perfil == 'doador':
        filtro = Q(lote__estabelecimento__usuario=usuario)
    else:
        filtro = Q(usuario=usuario)
    reservas = (
        Reserva.objects
        .filter(filtro, status=Reserva.Status.CONFIRMADA, data_confirmacao__isnull=False)
        .select_related('lote', 'lote__categoria', 'lote__alimento', 'lote__estabelecimento', 'usuario')
        .order_by('-data_confirmacao')
    )
    return [
        Retirada(reserva=r, quando=r.data_confirmacao, kg=r.lote.peso_kg, co2_kg=r.lote.co2_evitado_kg)
        for r in reservas
    ]


def _chave_mes(momento):
    local = timezone.localtime(momento)
    return local.year, local.month


def _mes_anterior(chave):
    ano, mes = chave
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def totais_por_mes(retiradas, meses=MESES_NO_GRAFICO, hoje=None):
    """Últimos `meses` meses (o atual por último), com zero nos meses sem retirada."""
    atual = _chave_mes(hoje or timezone.now())
    chaves = [atual]
    while len(chaves) < meses:
        chaves.insert(0, _mes_anterior(chaves[0]))
    por_mes = OrderedDict((chave, Totais()) for chave in chaves)
    for retirada in retiradas:
        chave = _chave_mes(retirada.quando)
        if chave in por_mes:
            por_mes[chave].somar(retirada)
    return por_mes


def rotulo_mes(chave):
    return f'{MESES[chave[1] - 1]}/{str(chave[0])[2:]}'


def variacao(atual, anterior):
    """Texto da tendência do mês: percentual sobre o mês anterior."""
    if not anterior:
        return 'Novo este mês' if atual else 'Sem retiradas este mês'
    percentual = ((atual - anterior) / anterior * 100).quantize(Decimal('1'))
    return f'{percentual:+}% este mês'
