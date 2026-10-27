from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from . import tokens
from .forms import CadastroUsuarioForm, EstabelecimentoForm, LoginForm
from .models import Usuario

# Textos de cada perfil usados nas telas de login e cadastro.
PERFIS = {
    Usuario.Perfil.PF: {
        'rotulo': 'Consumidor',
        'login_descricao': 'Login para consumidores encontrarem alimentos próximos do vencimento disponíveis para retirada na plataforma Prato Cheio.',
        'cadastro_descricao': 'Crie sua conta de consumidor no Prato Cheio e compre alimentos de qualidade próximos do vencimento.',
        'nome_label': 'Nome completo',
        'precisa_estabelecimento': False,
    },
    Usuario.Perfil.PJ: {
        'rotulo': 'Doador',
        'login_descricao': 'Login para estabelecimentos doadores cadastrarem lotes de alimentos e acompanharem seu impacto na plataforma Prato Cheio.',
        'cadastro_descricao': 'Cadastre seu mercado, padaria ou restaurante no Prato Cheio para doar ou vender excedentes de alimentos.',
        'nome_label': 'Nome fantasia',
        'precisa_estabelecimento': True,
    },
    Usuario.Perfil.ONG: {
        'rotulo': 'Instituição',
        'login_descricao': 'Login para instituições e ONGs reservarem lotes de alimentos doados na plataforma Prato Cheio.',
        'cadastro_descricao': 'Cadastre sua instituição no Prato Cheio para reservar alimentos doados e acompanhar o impacto gerado.',
        'nome_label': 'Nome da instituição',
        'precisa_estabelecimento': True,
    },
}

# Limite simples contra tentativas repetidas de senha (por perfil, IP e e-mail).
MAX_FALHAS = 5
BLOQUEIO_SEGUNDOS = 300


def index(request):
    """Tela inicial: escolha do perfil de acesso."""
    if request.usuario:
        return redirect('metricas:painel')
    return render(request, 'usuarios/index.html')


@never_cache
def login_view(request, perfil):
    """Valida e-mail e senha e grava os cookies JWT."""
    if request.usuario:
        return redirect('metricas:painel')

    info = PERFIS[perfil]
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].lower()
        chave = f'login:{perfil}:{request.META.get("REMOTE_ADDR", "")}:{email}'

        if cache.get(chave, 0) >= MAX_FALHAS:
            form.add_error(None, 'Muitas tentativas. Aguarde alguns minutos e tente de novo.')
        else:
            usuario = Usuario.objects.filter(email=email).first()
            if usuario is None:
                make_password(form.cleaned_data['senha'])  # gasta o mesmo tempo de um login real
            senha_ok = usuario is not None and usuario.check_password(form.cleaned_data['senha'])

            if not senha_ok or usuario.tipo_perfil != perfil:
                cache.set(chave, cache.get(chave, 0) + 1, BLOQUEIO_SEGUNDOS)
                form.add_error(None, 'E-mail ou senha incorretos para este perfil.')
            elif usuario.status_conta == Usuario.Status.PENDENTE:
                form.add_error(None, 'Seu cadastro ainda está em análise. Avisaremos quando for aprovado.')
            elif not usuario.pode_entrar:
                form.add_error(None, 'Este cadastro não foi aprovado. Entre em contato com a equipe Prato Cheio.')
            else:
                cache.delete(chave)
                resposta = redirect('metricas:painel')
                tokens.emitir_cookies(resposta, usuario)
                return resposta

    return render(request, 'usuarios/login.html', {
        'form': form,
        'perfil': perfil,
        'info': info,
    })


@never_cache
def cadastro_view(request, perfil):
    """Cria o usuario (e o estabelecimento, no caso de PJ e ONG)."""
    if request.usuario:
        return redirect('metricas:painel')

    info = PERFIS[perfil]
    usuario_form = CadastroUsuarioForm(request.POST or None, rotulo_nome=info['nome_label'])
    estabelecimento_form = (
        EstabelecimentoForm(request.POST or None, perfil=perfil)
        if info['precisa_estabelecimento'] else None
    )
    formularios = [f for f in (usuario_form, estabelecimento_form) if f is not None]

    if request.method == 'POST' and all([f.is_valid() for f in formularios]):
        with transaction.atomic():
            usuario = usuario_form.save(commit=False)
            usuario.tipo_perfil = perfil
            # Consumidor entra direto; PJ e ONG aguardam a aprovacao da equipe.
            usuario.status_conta = (
                Usuario.Status.PENDENTE if info['precisa_estabelecimento'] else Usuario.Status.APROVADO
            )
            usuario.save()
            if estabelecimento_form is not None:
                estabelecimento = estabelecimento_form.save(commit=False)
                estabelecimento.usuario = usuario
                estabelecimento.save()

        if info['precisa_estabelecimento']:
            messages.success(
                request,
                'Cadastro recebido! Nossa equipe vai analisar os dados e liberar o acesso em breve.',
            )
        else:
            messages.success(request, 'Conta criada! Entre com seu e-mail e senha.')
        return redirect(f'usuarios:login_{perfil}')

    return render(request, 'usuarios/cadastro.html', {
        'perfil': perfil,
        'info': info,
        'usuario_form': usuario_form,
        'estabelecimento_form': estabelecimento_form,
        'formularios': formularios,
    })


@require_POST
def sair(request):
    """Logout: apaga os cookies JWT."""
    request.usuario = None  # impede o middleware de renovar o cookie nesta resposta
    resposta = redirect('usuarios:index')
    tokens.limpar_cookies(resposta)
    return resposta
