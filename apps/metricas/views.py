from django.shortcuts import redirect, render

from apps.auth.decorators import login_obrigatorio
from apps.usuarios.perfis import PERFIS, url_painel_do_usuario

# Dados estáticos do protótipo. Serão substituídos por agregações sobre os
# lotes com status 'retirado': kg salvos = soma de peso_kg; CO₂ evitado =
# soma de Lote.co2_evitado_kg; refeições estimadas = kg salvos / 0,4 kg.
_RETIRADA_CONFIRMADA = ('Retirada confirmada', 'Instituição Esperança retirou 15kg de hortifruti.')
_LOTE_RESGATADO = ('Lote resgatado', 'Você resgatou 15kg de hortifruti no Mercado Bem Te Vi.')

PAINEIS = {
    'doador': {
        'titulo': 'Painel do Doador',
        'descricao': 'Painel do doador com métricas de impacto ambiental, alimentos salvos e refeições geradas a partir dos lotes doados.',
        'co2_kg': '3,000',
        'alimentos_t': '1.2',
        'refeicoes': '3,000',
        'sufixo_rotulo': '',
        'titulo_atividades': 'Últimas Retiradas',
        'atividade': _RETIRADA_CONFIRMADA,
    },
    'consumidor': {
        'titulo': 'Painel do Consumidor',
        'descricao': 'Painel do consumidor com o histórico de retiradas e o impacto ambiental gerado pelos alimentos resgatados.',
        'co2_kg': '750',
        'alimentos_t': '0.3',
        'refeicoes': '750',
        'sufixo_rotulo': ' (Sua contribuição)',
        'titulo_atividades': 'Seus Resgates',
        'atividade': _LOTE_RESGATADO,
    },
    'ong': {
        'titulo': 'Painel da ONG',
        'descricao': 'Painel da ONG com o histórico de resgates e o impacto ambiental gerado pelos lotes de alimentos recebidos.',
        'co2_kg': '2,000',
        'alimentos_t': '0.8',
        'refeicoes': '2,000',
        'sufixo_rotulo': ' (Sua contribuição)',
        'titulo_atividades': 'Seus Resgates',
        'atividade': _LOTE_RESGATADO,
    },
}


@login_obrigatorio()
def painel(request, perfil):
    if request.user.tipo_perfil != perfil:
        return redirect(url_painel_do_usuario(request.user))
    dados = PAINEIS[perfil]
    titulo_atividade, texto_atividade = dados['atividade']
    sufixo = dados['sufixo_rotulo']
    contexto = {
        'perfil': PERFIS[perfil],
        'ativo': 'painel',
        'titulo': dados['titulo'],
        'descricao': dados['descricao'],
        'metricas': [
            {'icone': '◌', 'tendencia': '+12% este mês', 'valor': dados['co2_kg'], 'unidade': 'kg', 'rotulo': f'CO₂ Evitado{sufixo}'},
            {'icone': '□', 'tendencia': '+3% este mês', 'valor': dados['alimentos_t'], 'unidade': 't', 'rotulo': f'Alimentos Salvos{sufixo}'},
            {'icone': '🌿', 'tendencia': '+8% este mês', 'valor': dados['refeicoes'], 'unidade': '', 'rotulo': f'Refeições Estimadas{sufixo}'},
        ],
        'titulo_atividades': dados['titulo_atividades'],
        'atividades': [
            {'titulo': titulo_atividade, 'texto': texto_atividade, 'quando': f'Há {horas} horas'}
            for horas in (2, 4, 6)
        ],
    }
    return render(request, 'metricas/painel.html', contexto)
