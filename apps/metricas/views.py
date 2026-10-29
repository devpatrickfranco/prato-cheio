from decimal import Decimal

from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.formats import number_format

from apps.auth.decorators import login_obrigatorio
from apps.usuarios.perfis import PERFIS, url_painel_do_usuario

from . import servicos

TEXTOS = {
    'doador': {
        'titulo': 'Painel do Doador',
        'descricao': 'Painel do doador com métricas de impacto ambiental, alimentos salvos e refeições geradas a partir dos lotes doados.',
        'sufixo_rotulo': '',
        'titulo_atividades': 'Últimas Retiradas',
        'vazio': 'Nenhuma retirada confirmada ainda. Quando um receptor retirar um lote, confirme em Meus Lotes.',
    },
    'consumidor': {
        'titulo': 'Painel do Consumidor',
        'descricao': 'Painel do consumidor com o histórico de retiradas e o impacto ambiental gerado pelos alimentos resgatados.',
        'sufixo_rotulo': ' (Sua contribuição)',
        'titulo_atividades': 'Seus Resgates',
        'vazio': 'Você ainda não retirou nenhum lote. Reserve um lote em Explorar Lotes.',
    },
    'ong': {
        'titulo': 'Painel da ONG',
        'descricao': 'Painel da ONG com o histórico de resgates e o impacto ambiental gerado pelos lotes de alimentos recebidos.',
        'sufixo_rotulo': ' (Sua contribuição)',
        'titulo_atividades': 'Seus Resgates',
        'vazio': 'Sua instituição ainda não retirou nenhum lote. Reserve um lote em Explorar Lotes.',
    },
}


def _numero(valor, casas=0):
    return number_format(valor, decimal_pos=casas, use_l10n=True, force_grouping=True)


def _alimentos_salvos(kg):
    """Toneladas a partir de 1 t; abaixo disso, quilos."""
    if kg >= 1000:
        return _numero(kg / 1000, 2), 't'
    return _numero(kg, 1), 'kg'


def _atividade(perfil, retirada):
    lote = retirada.lote
    quilos = _numero(retirada.kg, 1)
    if perfil == 'doador':
        titulo = 'Retirada confirmada'
        texto = f'{retirada.reserva.usuario.nome} retirou {quilos} kg: {lote.descricao}.'
    else:
        titulo = 'Lote resgatado'
        texto = f'Você resgatou {quilos} kg de {lote.descricao} em {lote.estabelecimento.razao_social}.'
    return {'titulo': titulo, 'texto': texto, 'quando': retirada.quando}


def _contexto_base(request, perfil):
    textos = TEXTOS[perfil]
    retiradas = servicos.retiradas_do_usuario(request.user)
    por_mes = servicos.totais_por_mes(retiradas)
    meses = list(por_mes.values())
    mes_atual, mes_anterior = meses[-1], meses[-2]
    total = servicos.Totais()
    for retirada in retiradas:
        total.somar(retirada)
    return textos, retiradas, por_mes, mes_atual, mes_anterior, total


@login_obrigatorio()
def painel(request, perfil):
    if perfil not in TEXTOS:
        raise Http404
    if request.user.tipo_perfil != perfil:
        return redirect(url_painel_do_usuario(request.user))
    textos, retiradas, por_mes, atual, anterior, total = _contexto_base(request, perfil)
    sufixo = textos['sufixo_rotulo']
    valor_alimentos, unidade_alimentos = _alimentos_salvos(total.kg)

    maior = max((mes.co2_kg for mes in por_mes.values()), default=Decimal('0'))
    grafico = [
        {
            'rotulo': servicos.rotulo_mes(chave),
            'co2': _numero(mes.co2_kg, 1),
            'altura': int(mes.co2_kg / maior * 100) if maior else 0,
        }
        for chave, mes in por_mes.items()
    ]
    contexto = {
        'perfil': PERFIS[perfil],
        'ativo': 'painel',
        'titulo': textos['titulo'],
        'descricao': textos['descricao'],
        'metricas': [
            {'icone': '◌', 'tendencia': servicos.variacao(atual.co2_kg, anterior.co2_kg), 'valor': _numero(total.co2_kg, 1), 'unidade': 'kg', 'rotulo': f'CO₂ Evitado{sufixo}'},
            {'icone': '□', 'tendencia': servicos.variacao(atual.kg, anterior.kg), 'valor': valor_alimentos, 'unidade': unidade_alimentos, 'rotulo': f'Alimentos Salvos{sufixo}'},
            {'icone': '🌿', 'tendencia': servicos.variacao(atual.refeicoes, anterior.refeicoes), 'valor': _numero(total.refeicoes), 'unidade': '', 'rotulo': f'Refeições Estimadas{sufixo}'},
        ],
        'grafico': grafico,
        'titulo_atividades': textos['titulo_atividades'],
        'atividades': [_atividade(perfil, r) for r in retiradas[:5]],
        'texto_sem_atividades': textos['vazio'],
    }
    return render(request, 'metricas/painel.html', contexto)


@login_obrigatorio()
def relatorio(request, perfil):
    """Relatório completo: totais por mês e todas as retiradas confirmadas."""
    if perfil not in TEXTOS:
        raise Http404
    if request.user.tipo_perfil != perfil:
        return redirect(url_painel_do_usuario(request.user))
    textos, retiradas, _, _, _, total = _contexto_base(request, perfil)
    por_mes = servicos.totais_por_mes(retiradas, meses=12)
    contexto = {
        'perfil': PERFIS[perfil],
        'ativo': 'painel',
        'titulo': 'Relatório de Impacto',
        'descricao': f'Relatório completo de impacto ambiental: totais por mês e histórico de retiradas. {textos["descricao"]}',
        'total': {'kg': _numero(total.kg, 1), 'co2': _numero(total.co2_kg, 1), 'refeicoes': _numero(total.refeicoes), 'retiradas': total.retiradas},
        'meses': [
            {'rotulo': servicos.rotulo_mes(chave), 'retiradas': mes.retiradas, 'kg': _numero(mes.kg, 1), 'co2': _numero(mes.co2_kg, 1), 'refeicoes': _numero(mes.refeicoes)}
            for chave, mes in reversed(por_mes.items())
        ],
        'retiradas': [
            {
                'quando': r.quando, 'descricao': r.lote.descricao, 'categoria': r.lote.categoria.nome,
                'contraparte': r.reserva.usuario.nome if perfil == 'doador' else r.lote.estabelecimento.razao_social,
                'kg': _numero(r.kg, 1), 'co2': _numero(r.co2_kg, 1),
            }
            for r in retiradas
        ],
        'rotulo_contraparte': 'Retirado por' if perfil == 'doador' else 'Estabelecimento',
    }
    return render(request, 'metricas/relatorio.html', contexto)
