"""Transporte dos tokens JWT em cookies HttpOnly para as páginas web."""
from django.conf import settings

from .tokens import emitir_access, emitir_tokens

ACCESS_COOKIE = 'pc_access'
REFRESH_COOKIE = 'pc_refresh'


def _definir(resposta, nome, valor, validade):
    resposta.set_cookie(
        nome, valor,
        max_age=int(validade.total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite='Lax',
    )


def definir_access(resposta, usuario):
    _definir(resposta, ACCESS_COOKIE, emitir_access(usuario), settings.JWT_ACCESS_TTL)


def definir_cookies(resposta, usuario):
    tokens = emitir_tokens(usuario)
    _definir(resposta, ACCESS_COOKIE, tokens['access'], settings.JWT_ACCESS_TTL)
    _definir(resposta, REFRESH_COOKIE, tokens['refresh'], settings.JWT_REFRESH_TTL)


def apagar_cookies(resposta):
    resposta.delete_cookie(ACCESS_COOKIE, samesite='Lax')
    resposta.delete_cookie(REFRESH_COOKIE, samesite='Lax')
