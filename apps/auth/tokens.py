"""Emissão, validação e revogação dos tokens JWT (HS256)."""
from uuid import uuid4

import jwt
from django.conf import settings
from django.utils import timezone

ALGORITMO = 'HS256'
ACCESS = 'access'
REFRESH = 'refresh'


class TokenInvalido(Exception):
    pass


def _emitir(usuario, tipo, validade):
    agora = timezone.now()
    payload = {
        'sub': str(usuario.pk),
        'tipo': tipo,
        'perfil': usuario.tipo_perfil,
        'jti': uuid4().hex,
        'iat': agora,
        'exp': agora + validade,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITMO)


def emitir_access(usuario):
    return _emitir(usuario, ACCESS, settings.JWT_ACCESS_TTL)


def emitir_tokens(usuario):
    return {
        'access': emitir_access(usuario),
        'refresh': _emitir(usuario, REFRESH, settings.JWT_REFRESH_TTL),
    }


def decodificar(token, tipo):
    """Valida assinatura, expiração, tipo e revogação; devolve o payload."""
    from .models import TokenRevogado

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[ALGORITMO],
            options={'require': ['exp', 'iat', 'sub', 'jti']},
        )
    except jwt.InvalidTokenError as erro:
        raise TokenInvalido(str(erro)) from erro
    if payload.get('tipo') != tipo:
        raise TokenInvalido('Tipo de token incorreto.')
    if TokenRevogado.objects.filter(jti=payload['jti']).exists():
        raise TokenInvalido('Token revogado.')
    return payload


def revogar(token):
    """Coloca o token na lista de revogação. Devolve False se ele já não era válido."""
    from datetime import datetime, timezone as fuso

    from .models import TokenRevogado

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITMO])
    except jwt.InvalidTokenError:
        return False  # expirado ou forjado: não há o que revogar
    TokenRevogado.objects.get_or_create(
        jti=payload['jti'], defaults={'expira_em': datetime.fromtimestamp(payload['exp'], tz=fuso.utc)},
    )
    return True
