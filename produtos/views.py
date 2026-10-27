from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from usuarios.decorators import jwt_required
from usuarios.models import Estabelecimento, Usuario

from . import services
from .forms import LoteForm
from .models import Categoria, Lote, Reserva
from .services import RegraDeNegocio

PF, PJ, ONG = Usuario.Perfil.PF, Usuario.Perfil.PJ, Usuario.Perfil.ONG


def _executar(request, acao, *args, sucesso, destino):
    """Roda uma regra de negócio e converte o resultado em mensagem para o usuário."""
    try:
        acao(*args)
    except RegraDeNegocio as erro:
        messages.error(request, str(erro))
    else:
        messages.success(request, sucesso)
    return redirect(destino)


# ---------------------------------------------------------------- vitrine


@jwt_required(PF, PJ, ONG)
def explorar(request):
    """Vitrine de lotes com filtro por busca, bairro e categoria."""
    services.expirar_pendencias()
    base = services.lotes_da_vitrine(request.usuario)

    busca = request.GET.get('q', '').strip()
    bairro = request.GET.get('bairro', '').strip()
    categoria = request.GET.get('categoria', '').strip()

    lotes = base
    if busca:
        lotes = lotes.filter(
            Q(descricao__icontains=busca) | Q(estabelecimento__usuario__nome__icontains=busca)
        )
    if bairro:
        lotes = lotes.filter(estabelecimento__bairro=bairro)
    if categoria.isdigit():
        lotes = lotes.filter(categoria_id=int(categoria))

    bairros = sorted(set(base.values_list('estabelecimento__bairro', flat=True)))
    return render(request, 'produtos/explorar.html', {
        'lotes': lotes,
        'categorias': Categoria.objects.all(),
        'bairros': bairros,
        'filtros': {'q': busca, 'bairro': bairro, 'categoria': categoria},
        'filtrando': bool(busca or bairro or categoria),
    })


@jwt_required(PF, PJ, ONG)
@require_POST
def reservar_lote(request, lote_id):
    try:
        services.reservar(lote_id, request.usuario, request.POST.get('observacao', ''))
    except RegraDeNegocio as erro:
        messages.error(request, str(erro))
        return redirect('produtos:explorar')
    messages.success(request, 'Lote reservado! Veja abaixo o endereço e o horário da retirada.')
    return redirect('produtos:minhas_reservas')


@jwt_required(PF, PJ, ONG)
def minhas_reservas(request):
    services.expirar_pendencias()
    reservas = Reserva.objects.filter(usuario=request.usuario).select_related(
        'lote__categoria', 'lote__estabelecimento__usuario'
    )
    return render(request, 'produtos/minhas-reservas.html', {
        'ativas': [r for r in reservas if r.status == Reserva.Status.ATIVA],
        'historico': [r for r in reservas if r.status != Reserva.Status.ATIVA],
    })


@jwt_required(PF, PJ, ONG)
@require_POST
def cancelar_reserva(request, reserva_id):
    return _executar(
        request, services.cancelar_reserva, reserva_id, request.usuario,
        sucesso='Reserva cancelada. O lote voltou para a vitrine.',
        destino='produtos:minhas_reservas',
    )


# ------------------------------------------------------------ doador (PJ)


def _estabelecimento_do_doador(request):
    return Estabelecimento.objects.filter(usuario=request.usuario).first()


@jwt_required(PJ)
def meus_lotes(request):
    services.expirar_pendencias()
    lotes = (
        Lote.objects.filter(estabelecimento__usuario=request.usuario)
        .select_related('categoria')
        .prefetch_related(Prefetch(
            'reservas',
            queryset=Reserva.objects.filter(status=Reserva.Status.ATIVA).select_related('usuario'),
            to_attr='reservas_ativas',
        ))
    )
    em_andamento = (Lote.Status.DISPONIVEL, Lote.Status.RESERVADO)
    return render(request, 'produtos/meus-lotes.html', {
        'ativos': [l for l in lotes if l.status in em_andamento],
        'historico': [l for l in lotes if l.status not in em_andamento],
    })


@jwt_required(PJ)
def lote_novo(request):
    estabelecimento = _estabelecimento_do_doador(request)
    if estabelecimento is None:
        messages.error(request, 'Seu cadastro não tem um estabelecimento. Fale com a equipe Prato Cheio.')
        return redirect('metricas:painel')

    form = LoteForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        lote = form.save(commit=False)
        lote.estabelecimento = estabelecimento
        lote.save()
        messages.success(request, 'Lote publicado na vitrine.')
        return redirect('produtos:meus_lotes')
    return render(request, 'produtos/lote-form.html', {'form': form, 'editando': False})


@jwt_required(PJ)
def lote_editar(request, lote_id):
    lote = get_object_or_404(Lote, pk=lote_id, estabelecimento__usuario=request.usuario)
    if not lote.editavel:
        messages.error(request, 'Só é possível editar lotes que ainda estão disponíveis.')
        return redirect('produtos:meus_lotes')

    form = LoteForm(request.POST or None, request.FILES or None, instance=lote)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Lote atualizado.')
        return redirect('produtos:meus_lotes')
    return render(request, 'produtos/lote-form.html', {'form': form, 'editando': True, 'lote': lote})


@jwt_required(PJ)
@require_POST
def lote_remover(request, lote_id):
    return _executar(
        request, services.remover_lote, lote_id, request.usuario,
        sucesso='Lote removido da vitrine.', destino='produtos:meus_lotes',
    )


@jwt_required(PJ)
@require_POST
def confirmar_retirada(request, reserva_id):
    return _executar(
        request, services.confirmar_retirada, reserva_id, request.usuario,
        sucesso='Retirada confirmada. O impacto já entrou nas suas métricas.',
        destino='produtos:meus_lotes',
    )


@jwt_required(PJ)
@require_POST
def nao_retirado(request, reserva_id):
    return _executar(
        request, services.marcar_nao_retirado, reserva_id, request.usuario,
        sucesso='Lote marcado como não retirado.', destino='produtos:meus_lotes',
    )
