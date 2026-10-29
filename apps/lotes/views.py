from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.auth.decorators import login_obrigatorio
from apps.usuarios.models import Estabelecimento
from apps.usuarios.perfis import PERFIS

from . import services
from .forms import LoteForm
from .models import Lote, Reserva
from .selectors import lotes_na_vitrine, opcoes_de_filtro


def _numero(valor, minimo, maximo):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if minimo <= numero <= maximo else None


def _inteiro(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _origem(request):
    """Localização do navegador (?lat=&lon=) ou, na falta dela, a do cadastro."""
    lat = _numero(request.GET.get('lat'), -90, 90)
    lon = _numero(request.GET.get('lon'), -180, 180)
    if lat is not None and lon is not None:
        return (lat, lon), True
    return request.user.coordenadas, False


def _executar(request, acao, *args, sucesso):
    """Roda uma regra de negócio e converte o resultado em mensagem para o usuário."""
    try:
        acao(*args)
    except services.RegraDeNegocio as erro:
        messages.error(request, str(erro))
        return False
    messages.success(request, sucesso)
    return True


# Receptores (consumidor e ONG)

@login_obrigatorio('consumidor', 'ong')
def explorar(request):
    services.atualizar_pendencias()
    origem, do_navegador = _origem(request)
    raio_km = _numero(request.GET.get('raio'), 0.1, 20000)
    busca = request.GET.get('q', '').strip()
    categoria_id = _inteiro(request.GET.get('categoria'))
    bairro = request.GET.get('bairro', '').strip()
    categorias, bairros = opcoes_de_filtro()
    contexto = {
        'perfil': PERFIS[request.user.tipo_perfil],
        'ativo': 'explorar',
        'lotes': lotes_na_vitrine(origem, raio_km, busca=busca, categoria_id=categoria_id, bairro=bairro),
        'origem': origem,
        'origem_do_navegador': do_navegador,
        'raio': request.GET.get('raio', '') if raio_km is not None else '',
        'busca': busca,
        'categorias': categorias,
        'categoria_id': categoria_id,
        'bairros': bairros,
        'bairro': bairro,
        'filtrando': bool(busca or categoria_id or bairro or raio_km is not None),
    }
    return render(request, 'lotes/explorar.html', contexto)


@login_obrigatorio('consumidor', 'ong')
@require_POST
def reservar(request, pk):
    if _executar(request, services.reservar_lote, request.user, pk, sucesso='Lote reservado! Retire dentro da janela informada.'):
        return redirect('lotes:minhas_reservas')
    return redirect('lotes:explorar')


@login_obrigatorio('consumidor', 'ong')
def minhas_reservas(request):
    services.atualizar_pendencias()
    reservas = (
        Reserva.objects
        .filter(usuario=request.user)
        .select_related('lote', 'lote__estabelecimento', 'lote__categoria')
        .order_by('-data_reserva')
    )
    contexto = {'perfil': PERFIS[request.user.tipo_perfil], 'ativo': 'reservas', 'reservas': reservas}
    return render(request, 'lotes/minhas_reservas.html', contexto)


@login_obrigatorio('consumidor', 'ong')
@require_POST
def cancelar_reserva(request, pk):
    _executar(request, services.cancelar_reserva, request.user, pk, sucesso='Reserva cancelada. O lote voltou para a vitrine.')
    return redirect('lotes:minhas_reservas')


# Doador

@login_obrigatorio('doador')
def meus_lotes(request):
    services.atualizar_pendencias()
    lotes = (
        Lote.objects
        .filter(estabelecimento__usuario=request.user)
        .select_related('categoria')
        .prefetch_related('reservas__usuario')
        .order_by('data_validade')
    )
    for lote in lotes:
        lote.reserva_ativa = next((r for r in lote.reservas.all() if r.status == Reserva.Status.ATIVA), None)
        lote.excluivel = lote.status not in services.STATUS_NAO_EXCLUIVEIS
    contexto = {'perfil': PERFIS['doador'], 'ativo': 'meus_lotes', 'lotes': lotes}
    return render(request, 'lotes/meus_lotes.html', contexto)


def _formulario(request, form, titulo):
    contexto = {'perfil': PERFIS['doador'], 'ativo': 'novo_lote', 'form': form, 'titulo': titulo}
    return render(request, 'lotes/formulario_lote.html', contexto)


@login_obrigatorio('doador')
def novo_lote(request):
    try:
        estabelecimento = request.user.estabelecimento
    except Estabelecimento.DoesNotExist:
        messages.error(request, 'Cadastre os dados do seu estabelecimento antes de anunciar lotes.')
        return redirect('usuarios:meu_estabelecimento')

    form = LoteForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        lote = form.save(commit=False)
        lote.estabelecimento = estabelecimento
        lote.save()
        messages.success(request, f'Lote "{lote.descricao}" anunciado.')
        return redirect('lotes:meus_lotes')
    return _formulario(request, form, 'Anunciar Lote')


@login_obrigatorio('doador')
def editar_lote(request, pk):
    # Só lotes ainda disponíveis do próprio estabelecimento podem ser editados.
    lote = get_object_or_404(
        Lote, pk=pk, estabelecimento__usuario=request.user, status=Lote.Status.DISPONIVEL,
    )
    form = LoteForm(request.POST or None, request.FILES or None, instance=lote)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Lote "{lote.descricao}" atualizado.')
        return redirect('lotes:meus_lotes')
    return _formulario(request, form, 'Editar Lote')


@login_obrigatorio('doador')
@require_POST
def excluir_lote(request, pk):
    try:
        descricao = services.excluir_lote(request.user, pk)
    except services.RegraDeNegocio as erro:
        messages.error(request, str(erro))
    else:
        messages.success(request, f'Lote "{descricao}" excluído.')
    return redirect('lotes:meus_lotes')


@login_obrigatorio('doador')
@require_POST
def registrar_retirada(request, pk):
    """O doador marca o lote reservado como retirado ou não retirado (campo `resultado`)."""
    resultado = request.POST.get('resultado')
    if resultado == 'retirado':
        _executar(request, services.confirmar_retirada, request.user, pk, sucesso='Retirada confirmada. O lote já conta no seu impacto.')
    elif resultado == 'nao_retirado':
        _executar(request, services.registrar_nao_retirada, request.user, pk, sucesso='Registrado como não retirado.')
    else:
        messages.error(request, 'Ação inválida.')
    return redirect('lotes:meus_lotes')
