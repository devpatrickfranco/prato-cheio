from django.conf import settings
from django.utils.cache import patch_vary_headers

from . import tokens
from .models import Usuario


class JWTAuthMiddleware:
    """Identifica o usuario pelo cookie JWT e o expõe em ``request.usuario``.

    Se o access token expirou mas o refresh ainda vale, emite um novo access.
    ``request.user`` (sessao do Django) continua sendo usado so pelo /admin/.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.usuario = None
        renovar = False

        usuario = self._usuario_do_token(request.COOKIES.get(settings.JWT_COOKIE_ACCESS), tokens.ACCESS)
        if usuario is None:
            usuario = self._usuario_do_token(
                request.COOKIES.get(settings.JWT_COOKIE_REFRESH), tokens.REFRESH
            )
            renovar = usuario is not None
        request.usuario = usuario

        response = self.get_response(request)

        # A view de logout zera request.usuario; nesse caso nao renovamos o cookie.
        if renovar and request.usuario is not None:
            tokens.definir_cookie_access(response, request.usuario)
        patch_vary_headers(response, ('Cookie',))
        return response

    @staticmethod
    def _usuario_do_token(token, tipo):
        carga = tokens.decodificar_token(token, tipo)
        if carga is None:
            return None
        try:
            usuario = Usuario.objects.get(pk=int(carga['sub']))
        except (Usuario.DoesNotExist, ValueError):
            return None
        # Conta recusada ou desativada perde o acesso mesmo com token valido.
        return usuario if usuario.pode_entrar else None
