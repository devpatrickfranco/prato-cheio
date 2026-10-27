"""Regras de negócio de lotes e reservas, fora das views para facilitar os testes."""

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from usuarios.models import Usuario

from .models import Lote, Reserva


class RegraDeNegocio(Exception):
    """Violação de regra: a mensagem é mostrada ao usuário."""


def lotes_da_vitrine(usuario):
    """Lotes que o usuário pode reservar agora.

    Doações são exclusivas das ONGs; vendas, de consumidores e estabelecimentos.
    """
    agora = timezone.now()
    lotes = Lote.objects.filter(
        status=Lote.Status.DISPONIVEL,
        data_validade__gte=timezone.localdate(agora),
        retirada_fim__gt=agora,
    ).select_related('estabelecimento__usuario', 'categoria')

    if usuario.tipo_perfil == Usuario.Perfil.ONG:
        lotes = lotes.filter(tipo=Lote.Tipo.DOACAO)
    else:
        lotes = lotes.filter(tipo=Lote.Tipo.VENDA)
    return lotes.exclude(estabelecimento__usuario=usuario)


def expirar_pendencias(agora=None):
    """Atualiza o que venceu: reservas não retiradas e lotes fora do prazo."""
    agora = agora or timezone.now()
    with transaction.atomic():
        reservas = Reserva.objects.filter(status=Reserva.Status.ATIVA, data_expiracao__lt=agora)
        lotes_ids = list(reservas.values_list('lote_id', flat=True))
        reservas.update(status=Reserva.Status.EXPIRADA)
        Lote.objects.filter(pk__in=lotes_ids, status=Lote.Status.RESERVADO).update(
            status=Lote.Status.NAO_RETIRADO
        )
        Lote.objects.filter(status=Lote.Status.DISPONIVEL).filter(
            Q(data_validade__lt=timezone.localdate(agora)) | Q(retirada_fim__lt=agora)
        ).update(status=Lote.Status.EXPIRADO)


def calcular_comissao(valor):
    """Comissão da plataforma sobre uma venda (percentual definido nas configurações)."""
    return (Decimal(valor) * settings.COMISSAO_PERCENTUAL / 100).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )


def _lote_travado(lote_id):
    try:
        return Lote.objects.select_for_update().get(pk=lote_id)
    except Lote.DoesNotExist:
        raise RegraDeNegocio('Lote não encontrado.')


@transaction.atomic
def reservar(lote_id, usuario, observacao=''):
    lote = _lote_travado(lote_id)
    agora = timezone.now()

    if (
        lote.status != Lote.Status.DISPONIVEL
        or lote.data_validade < timezone.localdate(agora)
        or lote.retirada_fim <= agora
    ):
        raise RegraDeNegocio('Este lote não está mais disponível.')
    if lote.estabelecimento.usuario_id == usuario.pk:
        raise RegraDeNegocio('Você não pode reservar o seu próprio lote.')
    if lote.tipo == Lote.Tipo.DOACAO and usuario.tipo_perfil != Usuario.Perfil.ONG:
        raise RegraDeNegocio('Lotes de doação são exclusivos para instituições.')
    if lote.tipo == Lote.Tipo.VENDA and usuario.tipo_perfil not in (
        Usuario.Perfil.PF, Usuario.Perfil.PJ
    ):
        raise RegraDeNegocio('Lotes à venda são para consumidores e estabelecimentos.')

    valor = lote.preco or Decimal('0')
    try:
        with transaction.atomic():
            reserva = Reserva.objects.create(
                lote=lote,
                usuario=usuario,
                data_expiracao=lote.retirada_fim,
                observacao=observacao[:200],
                valor=valor,
                comissao=calcular_comissao(valor) if lote.eh_venda else Decimal('0'),
            )
    except IntegrityError:
        raise RegraDeNegocio('Outra pessoa acabou de reservar este lote.')

    lote.status = Lote.Status.RESERVADO
    lote.save(update_fields=['status'])
    return reserva


def _reserva_ativa_travada(reserva_id):
    try:
        reserva = Reserva.objects.select_for_update().get(pk=reserva_id)
    except Reserva.DoesNotExist:
        raise RegraDeNegocio('Reserva não encontrada.')
    if reserva.status != Reserva.Status.ATIVA:
        raise RegraDeNegocio('Esta reserva não está mais ativa.')
    return reserva


@transaction.atomic
def cancelar_reserva(reserva_id, usuario):
    """Quem reservou desiste: o lote volta para a vitrine se ainda estiver no prazo."""
    reserva = _reserva_ativa_travada(reserva_id)
    if reserva.usuario_id != usuario.pk:
        raise RegraDeNegocio('Você só pode cancelar as suas reservas.')

    reserva.status = Reserva.Status.CANCELADA
    reserva.save(update_fields=['status'])

    lote = _lote_travado(reserva.lote_id)
    agora = timezone.now()
    no_prazo = lote.data_validade >= timezone.localdate(agora) and lote.retirada_fim > agora
    lote.status = Lote.Status.DISPONIVEL if no_prazo else Lote.Status.EXPIRADO
    lote.save(update_fields=['status'])


@transaction.atomic
def confirmar_retirada(reserva_id, doador):
    """O estabelecimento confirma que a retirada aconteceu (alimenta as métricas)."""
    reserva = _reserva_ativa_travada(reserva_id)
    lote = _lote_travado(reserva.lote_id)
    if lote.estabelecimento.usuario_id != doador.pk:
        raise RegraDeNegocio('Este lote pertence a outro estabelecimento.')

    reserva.status = Reserva.Status.CONFIRMADA
    reserva.data_confirmacao = timezone.now()
    reserva.save(update_fields=['status', 'data_confirmacao'])
    lote.status = Lote.Status.RETIRADO
    lote.save(update_fields=['status'])


@transaction.atomic
def marcar_nao_retirado(reserva_id, doador):
    """O estabelecimento informa que a pessoa não apareceu."""
    reserva = _reserva_ativa_travada(reserva_id)
    lote = _lote_travado(reserva.lote_id)
    if lote.estabelecimento.usuario_id != doador.pk:
        raise RegraDeNegocio('Este lote pertence a outro estabelecimento.')

    reserva.status = Reserva.Status.EXPIRADA
    reserva.save(update_fields=['status'])
    lote.status = Lote.Status.NAO_RETIRADO
    lote.save(update_fields=['status'])


@transaction.atomic
def remover_lote(lote_id, doador):
    """Retira da vitrine um lote que ainda não foi reservado."""
    lote = _lote_travado(lote_id)
    if lote.estabelecimento.usuario_id != doador.pk:
        raise RegraDeNegocio('Este lote pertence a outro estabelecimento.')
    if lote.status != Lote.Status.DISPONIVEL:
        raise RegraDeNegocio('Só é possível remover lotes que ainda estão disponíveis.')
    lote.delete()
