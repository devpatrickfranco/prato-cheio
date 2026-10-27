"""Cálculo dos indicadores de impacto (CO₂ evitado, alimentos salvos, refeições).

Só entram nas contas as reservas com retirada confirmada. O CO₂ vem do fator da
categoria do lote (``Categoria.fator_co2_kg``), que poderá ser atualizado quando a
base de dados de CO₂ em PDF for incorporada.
"""

from decimal import Decimal

from django.conf import settings
from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from produtos.models import Reserva
from usuarios.models import Usuario

ZERO = Decimal('0')
SAIDA_DECIMAL = DecimalField(max_digits=14, decimal_places=2)

# Gamificação do doador: nível conforme o total de alimentos salvos (kg).
NIVEIS = [
    (ZERO, 'Semente'),
    (Decimal('50'), 'Broto'),
    (Decimal('200'), 'Árvore'),
    (Decimal('500'), 'Floresta'),
]


def reservas_confirmadas(usuario):
    """Retiradas confirmadas que contam para o usuário.

    Doador: o que saiu do seu estabelecimento. Administrador: tudo.
    Demais perfis: o que eles mesmos retiraram.
    """
    reservas = Reserva.objects.filter(status=Reserva.Status.CONFIRMADA)
    if usuario.tipo_perfil == Usuario.Perfil.PJ:
        return reservas.filter(lote__estabelecimento__usuario=usuario)
    if usuario.tipo_perfil == Usuario.Perfil.ADMIN:
        return reservas
    return reservas.filter(usuario=usuario)


def _agregados():
    return {
        'lotes': Count('pk'),
        'kg': Sum('lote__peso_kg'),
        'co2': Sum(F('lote__peso_kg') * F('lote__categoria__fator_co2_kg'), output_field=SAIDA_DECIMAL),
    }


def _montar(kg, co2, lotes):
    kg = kg or ZERO
    co2 = co2 or ZERO
    return {
        'lotes': lotes or 0,
        'kg': kg,
        'co2': co2,
        'refeicoes': int((kg / settings.KG_POR_REFEICAO).to_integral_value()),
    }


def resumo(reservas):
    """Totais de um conjunto de reservas confirmadas."""
    dados = reservas.aggregate(**_agregados())
    return _montar(dados['kg'], dados['co2'], dados['lotes'])


def _mes_anterior(mes, quantos):
    ano, numero = mes.year, mes.month - quantos
    while numero < 1:
        numero += 12
        ano -= 1
    return mes.replace(year=ano, month=numero, day=1)


def serie_mensal(reservas, meses=6):
    """Totais por mês, do mais antigo para o atual, incluindo meses sem retirada."""
    hoje = timezone.localdate().replace(day=1)
    inicio = _mes_anterior(hoje, meses - 1)
    linhas = (
        reservas.filter(data_confirmacao__date__gte=inicio)
        .annotate(mes=TruncMonth('data_confirmacao'))
        .values('mes')
        .annotate(**_agregados())
    )
    por_mes = {timezone.localtime(l['mes']).date().replace(day=1): l for l in linhas}

    serie = []
    for posicao in range(meses):
        mes = _mes_anterior(hoje, meses - 1 - posicao)
        linha = por_mes.get(mes, {})
        item = _montar(linha.get('kg'), linha.get('co2'), linha.get('lotes'))
        item['mes'] = mes
        serie.append(item)
    return serie


def variacao_percentual(atual, anterior):
    """Variação em % entre dois valores; None quando não há base de comparação."""
    if not anterior:
        return None
    return int(((atual - anterior) / anterior * 100).to_integral_value())


def variacoes_do_mes(serie):
    """Compara o último mês da série com o anterior."""
    atual, anterior = serie[-1], serie[-2]
    return {
        chave: variacao_percentual(Decimal(atual[chave]), Decimal(anterior[chave]))
        for chave in ('co2', 'kg', 'refeicoes')
    }


def por_categoria(reservas):
    """Totais agrupados por categoria de alimento."""
    linhas = (
        reservas.values(nome=F('lote__categoria__nome'))
        .annotate(**_agregados())
        .order_by('-kg')
    )
    return [{'nome': l['nome'], **_montar(l['kg'], l['co2'], l['lotes'])} for l in linhas]


def nivel_do_doador(kg_total):
    """Nível atual e quanto falta para o próximo (None no nível máximo)."""
    atual = NIVEIS[0]
    for minimo, nome in NIVEIS:
        if kg_total >= minimo:
            atual = (minimo, nome)
    proximo = next(((m, n) for m, n in NIVEIS if m > atual[0]), None)
    if proximo is None:
        return {'nome': atual[1], 'proximo': None, 'faltam': None, 'meta': None, 'progresso': kg_total}
    return {
        'nome': atual[1],
        'proximo': proximo[1],
        'faltam': proximo[0] - kg_total,
        'meta': proximo[0],
        'progresso': kg_total,
    }
