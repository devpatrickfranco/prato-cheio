"""Regras de negócio do ciclo de vida de lotes e reservas.

Fluxo: disponível → reservado (reserva ativa) → retirado (reserva confirmada) ou
não retirado (doador registra) ou, sem retirada até o fim da janela, a reserva expira e o
lote volta a disponível. Lotes disponíveis cuja validade passou viram expirados.
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Lote, Reserva


class RegraDeNegocio(Exception):
    """Operação recusada; a mensagem é exibida ao usuário."""


def expirar_lotes(hoje=None):
    """Lotes disponíveis com validade vencida passam a `expirado`. Devolve quantos mudaram."""
    hoje = hoje or timezone.localdate()
    return Lote.objects.filter(status=Lote.Status.DISPONIVEL, data_validade__lt=hoje).update(status=Lote.Status.EXPIRADO)


def expirar_reservas(agora=None):
    """Reservas ativas vencidas viram `expirada` e o lote volta a `disponivel` (ou `expirado`)."""
    agora = agora or timezone.now()
    hoje = timezone.localdate(agora)
    vencidas = Reserva.objects.filter(status=Reserva.Status.ATIVA, data_expiracao__lt=agora).select_related('lote')
    total = 0
    for reserva in vencidas:
        with transaction.atomic():
            reserva.status = Reserva.Status.EXPIRADA
            reserva.save(update_fields=['status'])
            lote = reserva.lote
            if lote.status == Lote.Status.RESERVADO:
                lote.status = Lote.Status.DISPONIVEL if lote.data_validade >= hoje else Lote.Status.EXPIRADO
                lote.save(update_fields=['status'])
        total += 1
    return total


def atualizar_pendencias(agora=None):
    """Manutenção barata chamada antes de listar lotes; também roda em `atualizar_status`."""
    agora = agora or timezone.now()
    return expirar_reservas(agora), expirar_lotes(timezone.localdate(agora))


def reservar_lote(usuario, lote_id):
    """Cria a reserva do lote para um consumidor/ONG; vale até o fim da janela de retirada."""
    if usuario.tipo_perfil not in ('consumidor', 'ong'):
        raise RegraDeNegocio('Somente consumidores e ONGs podem reservar lotes.')
    atualizar_pendencias()
    agora = timezone.now()
    try:
        with transaction.atomic():
            lote = Lote.objects.select_for_update().filter(pk=lote_id).first()
            if lote is None:
                raise RegraDeNegocio('Lote não encontrado.')
            if lote.status != Lote.Status.DISPONIVEL:
                raise RegraDeNegocio('Este lote não está mais disponível.')
            if lote.data_validade < timezone.localdate(agora) or lote.retirada_fim <= agora:
                raise RegraDeNegocio('A janela de retirada deste lote já terminou.')
            reserva = Reserva.objects.create(lote=lote, usuario=usuario, data_expiracao=lote.retirada_fim)
            lote.status = Lote.Status.RESERVADO
            lote.save(update_fields=['status'])
    except IntegrityError as erro:  # outra reserva ativa criada ao mesmo tempo
        raise RegraDeNegocio('Este lote acabou de ser reservado por outra pessoa.') from erro
    return reserva


def cancelar_reserva(usuario, reserva_id):
    """O próprio receptor desiste da reserva; o lote volta para a vitrine."""
    with transaction.atomic():
        reserva = Reserva.objects.select_for_update().select_related('lote').filter(
            pk=reserva_id, usuario=usuario, status=Reserva.Status.ATIVA,
        ).first()
        if reserva is None:
            raise RegraDeNegocio('Reserva não encontrada ou já encerrada.')
        reserva.status = Reserva.Status.CANCELADA
        reserva.save(update_fields=['status'])
        reserva.lote.status = Lote.Status.DISPONIVEL
        reserva.lote.save(update_fields=['status'])
    atualizar_pendencias()
    return reserva


def _reserva_ativa_do_doador(doador, lote_id):
    reserva = Reserva.objects.select_for_update().select_related('lote').filter(
        lote_id=lote_id, lote__estabelecimento__usuario=doador, status=Reserva.Status.ATIVA,
    ).first()
    if reserva is None:
        raise RegraDeNegocio('Este lote não tem reserva ativa.')
    return reserva


def confirmar_retirada(doador, lote_id):
    """O doador confirma que o lote foi retirado: passa a contar nas métricas de impacto."""
    with transaction.atomic():
        reserva = _reserva_ativa_do_doador(doador, lote_id)
        reserva.status = Reserva.Status.CONFIRMADA
        reserva.data_confirmacao = timezone.now()
        reserva.save(update_fields=['status', 'data_confirmacao'])
        reserva.lote.status = Lote.Status.RETIRADO
        reserva.lote.save(update_fields=['status'])
    return reserva


def registrar_nao_retirada(doador, lote_id):
    """O doador registra que ninguém retirou o lote reservado."""
    with transaction.atomic():
        reserva = _reserva_ativa_do_doador(doador, lote_id)
        reserva.status = Reserva.Status.NAO_RETIRADA
        reserva.save(update_fields=['status'])
        reserva.lote.status = Lote.Status.NAO_RETIRADO
        reserva.lote.save(update_fields=['status'])
    return reserva


STATUS_NAO_EXCLUIVEIS = (Lote.Status.RESERVADO, Lote.Status.RETIRADO)


def excluir_lote(doador, lote_id):
    """Remove um lote do próprio doador. Lotes reservados ou retirados são histórico e ficam."""
    lote = Lote.objects.filter(pk=lote_id, estabelecimento__usuario=doador).first()
    if lote is None:
        raise RegraDeNegocio('Lote não encontrado.')
    if lote.status in STATUS_NAO_EXCLUIVEIS:
        raise RegraDeNegocio('Lotes reservados ou já retirados não podem ser excluídos. Registre a retirada antes.')
    descricao = lote.descricao
    if lote.foto:
        lote.foto.delete(save=False)
    lote.delete()
    return descricao
