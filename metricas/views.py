from django.shortcuts import render

from produtos import services as produtos_services
from produtos.models import Reserva
from usuarios.decorators import jwt_required
from usuarios.models import Usuario

from . import services

# Textos do painel conforme o perfil de quem está logado.
TEXTOS = {
    Usuario.Perfil.PJ: {
        'titulo': 'Painel do Doador',
        'descricao': 'Painel do doador com métricas de impacto ambiental, alimentos salvos e refeições geradas a partir dos lotes doados.',
        'sufixo': '',
        'atividade': 'Últimas Retiradas',
    },
    Usuario.Perfil.PF: {
        'titulo': 'Painel do Consumidor',
        'descricao': 'Painel do consumidor com o histórico de retiradas e o impacto ambiental gerado pelos alimentos resgatados.',
        'sufixo': ' (Sua contribuição)',
        'atividade': 'Seus Resgates',
    },
    Usuario.Perfil.ONG: {
        'titulo': 'Painel da Instituição',
        'descricao': 'Painel da instituição com o histórico de resgates e o impacto ambiental gerado pelos lotes de alimentos recebidos.',
        'sufixo': ' (Sua contribuição)',
        'atividade': 'Seus Resgates',
    },
    Usuario.Perfil.ADMIN: {
        'titulo': 'Painel da Plataforma',
        'descricao': 'Painel geral da plataforma com o impacto ambiental de todas as retiradas confirmadas.',
        'sufixo': ' (Plataforma)',
        'atividade': 'Últimas Retiradas',
    },
}


def _contexto_base(request):
    produtos_services.expirar_pendencias()
    reservas = services.reservas_confirmadas(request.usuario)
    serie = services.serie_mensal(reservas)
    return reservas, serie


@jwt_required()
def painel(request):
    """Painel de impacto, com o mesmo layout para todos os perfis."""
    reservas, serie = _contexto_base(request)
    total = services.resumo(reservas)
    ultimas = reservas.select_related(
        'usuario', 'lote__categoria', 'lote__estabelecimento__usuario'
    ).order_by('-data_confirmacao')[:5]

    contexto = {
        'textos': TEXTOS[request.usuario.tipo_perfil],
        'total': total,
        'variacoes': services.variacoes_do_mes(serie),
        'serie': serie,
        'maximo_co2': max([item['co2'] for item in serie] + [1]),
        'ultimas': ultimas,
    }
    if request.usuario.tipo_perfil == Usuario.Perfil.PJ:
        contexto['nivel'] = services.nivel_do_doador(total['kg'])
    return render(request, 'metricas/painel.html', contexto)


@jwt_required()
def relatorio(request):
    """Relatório completo: evolução mensal e totais por categoria."""
    reservas, serie = _contexto_base(request)
    return render(request, 'metricas/relatorio.html', {
        'textos': TEXTOS[request.usuario.tipo_perfil],
        'total': services.resumo(reservas),
        'serie': list(reversed(serie)),
        'categorias': services.por_categoria(reservas),
    })
