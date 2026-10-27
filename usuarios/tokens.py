"""Emissao e leitura dos tokens JWT (access e refresh).

Os tokens viajam em cookies HttpOnly, assim o JavaScript da pagina nao os enxerga
(protecao contra XSS). Como o navegador envia os cookies sozinho, o CSRF do Django
continua ativo nos formularios POST.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings

ACCESS = 'access'
REFRESH = 'refresh'


def _duracao(tipo):
    if tipo == ACCESS:
        return timedelta(minutes=settings.JWT_ACCESS_MINUTOS)
    return timedelta(days=settings.JWT_REFRESH_DIAS)


def gerar_token(usuario, tipo):
    """Cria um token assinado (HS256) para o usuario."""
    agora = datetime.now(timezone.utc)
    carga = {
        'sub': str(usuario.pk),
        'perfil': usuario.tipo_perfil,
        'tipo': tipo,
        'iat': agora,
        'exp': agora + _duracao(tipo),
        'jti': uuid.uuid4().hex,
    }
    return jwt.encode(carga, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decodificar_token(token, tipo):
    """Devolve a carga do token ou None se for invalido, expirado ou do tipo errado."""
    if not token:
        return None
    try:
        carga = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={'require': ['exp', 'iat', 'sub']},
        )
    except jwt.InvalidTokenError:
        return None
    if carga.get('tipo') != tipo:
        return None
    return carga


def _definir_cookie(response, nome, token, duracao):
    response.set_cookie(
        nome,
        token,
        max_age=int(duracao.total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite='Lax',
    )


def definir_cookie_access(response, usuario):
    _definir_cookie(
        response, settings.JWT_COOKIE_ACCESS, gerar_token(usuario, ACCESS), _duracao(ACCESS)
    )


def emitir_cookies(response, usuario):
    """Grava access e refresh na resposta (login)."""
    definir_cookie_access(response, usuario)
    _definir_cookie(
        response, settings.JWT_COOKIE_REFRESH, gerar_token(usuario, REFRESH), _duracao(REFRESH)
    )


def limpar_cookies(response):
    """Remove os dois cookies (logout)."""
    response.delete_cookie(settings.JWT_COOKIE_ACCESS, samesite='Lax')
    response.delete_cookie(settings.JWT_COOKIE_REFRESH, samesite='Lax')
