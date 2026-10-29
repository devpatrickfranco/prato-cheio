from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import redirect, render

from apps.auth.decorators import login_obrigatorio

from .forms import CadastroUsuarioForm, EstabelecimentoForm
from .geocodificacao import geocodificar
from .models import Estabelecimento
from .perfis import PERFIS


def index(request):
    return render(request, 'usuarios/index.html')


def _geocodificar_estabelecimento(estabelecimento):
    coordenadas = geocodificar(
        cidade=estabelecimento.cidade, uf=estabelecimento.uf, cep=estabelecimento.cep,
        logradouro=estabelecimento.logradouro, numero=estabelecimento.numero, bairro=estabelecimento.bairro,
    )
    estabelecimento.latitude, estabelecimento.longitude = coordenadas or (None, None)


def cadastro(request, perfil):
    """Cadastro de doador, consumidor ou ONG. A conta nasce `pendente` até o administrador aprovar."""
    perfil = PERFIS[perfil]
    form = CadastroUsuarioForm(request.POST or None, perfil=perfil)
    form_estabelecimento = EstabelecimentoForm(request.POST or None) if perfil.doador else None

    if request.method == 'POST' and form.is_valid() and (form_estabelecimento is None or form_estabelecimento.is_valid()):
        dados = form.cleaned_data
        Usuario = get_user_model()
        with transaction.atomic():
            usuario = Usuario(
                nome=dados['nome'], email=dados['email'], telefone=dados['telefone'].strip(),
                documento=dados.get('documento', ''), tipo_perfil=perfil.slug,
                status_conta=Usuario.StatusConta.PENDENTE,
            )
            usuario.set_password(dados['senha'])
            if dados.get('cep'):
                coordenadas = geocodificar(cep=dados['cep'])
                if coordenadas:
                    usuario.latitude, usuario.longitude = coordenadas
            usuario.save()
            if form_estabelecimento is not None:
                estabelecimento = form_estabelecimento.save(commit=False)
                estabelecimento.usuario = usuario
                _geocodificar_estabelecimento(estabelecimento)
                estabelecimento.save()
        messages.success(request, 'Cadastro enviado! Assim que a plataforma aprovar sua conta, você poderá entrar.')
        return redirect(perfil.url_login)

    contexto = {'perfil': perfil, 'form': form, 'form_estabelecimento': form_estabelecimento}
    return render(request, 'usuarios/cadastro.html', contexto)


@login_obrigatorio('doador')
def meu_estabelecimento(request):
    """O doador cadastra ou edita os dados do próprio estabelecimento."""
    estabelecimento = Estabelecimento.objects.filter(usuario=request.user).first()
    form = EstabelecimentoForm(request.POST or None, instance=estabelecimento)
    if request.method == 'POST' and form.is_valid():
        mudou = estabelecimento is None or form.endereco_mudou()
        estabelecimento = form.save(commit=False)
        estabelecimento.usuario = request.user
        if mudou:
            _geocodificar_estabelecimento(estabelecimento)
        estabelecimento.save()
        messages.success(request, 'Dados do estabelecimento salvos.')
        return redirect('usuarios:meu_estabelecimento')
    contexto = {'perfil': PERFIS['doador'], 'ativo': 'estabelecimento', 'form': form, 'estabelecimento': estabelecimento}
    return render(request, 'usuarios/meu_estabelecimento.html', contexto)
