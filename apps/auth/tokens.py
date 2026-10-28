"""Emissão e validação dos tokens JWT (HS256)."""
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
    """Valida assinatura, expiração e tipo; devolve o payload."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[ALGORITMO],
            options={'require': ['exp', 'iat', 'sub']},
        )
    except jwt.InvalidTokenError as erro:
        raise TokenInvalido(str(erro)) from erro
    if payload.get('tipo') != tipo:
        raise TokenInvalido('Tipo de token incorreto.')
    return payload
