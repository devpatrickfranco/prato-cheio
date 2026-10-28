from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.auth.decorators import login_obrigatorio
from apps.usuarios.models import Estabelecimento
from apps.usuarios.perfis import PERFIS

from .forms import LoteForm
from .models import Lote
from .selectors import lotes_na_vitrine


def _numero(valor, minimo, maximo):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if minimo <= numero <= maximo else None


def _origem(request):
    """Localização do navegador (?lat=&lon=) ou, na falta dela, a do cadastro."""
    lat = _numero(request.GET.get('lat'), -90, 90)
    lon = _numero(request.GET.get('lon'), -180, 180)
    if lat is not None and lon is not None:
        return (lat, lon), True
    return request.user.coordenadas, False


@login_obrigatorio('consumidor', 'ong')
def explorar(request):
    origem, do_navegador = _origem(request)
    raio_km = _numero(request.GET.get('raio'), 0.1, 20000)
    contexto = {
        'perfil': PERFIS[request.user.tipo_perfil],
        'ativo': 'explorar',
        'lotes': lotes_na_vitrine(origem, raio_km),
        'origem': origem,
        'origem_do_navegador': do_navegador,
        'raio': request.GET.get('raio', '') if raio_km is not None else '',
    }
    return render(request, 'lotes/explorar.html', contexto)


@login_obrigatorio('doador')
def meus_lotes(request):
    lotes = (
        Lote.objects
        .filter(estabelecimento__usuario=request.user)
        .select_related('categoria')
        .order_by('data_validade')
    )
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
        return redirect('lotes:meus_lotes')

    form = LoteForm(request.POST or None)
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
    form = LoteForm(request.POST or None, instance=lote)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Lote "{lote.descricao}" atualizado.')
        return redirect('lotes:meus_lotes')
    return _formulario(request, form, 'Editar Lote')
