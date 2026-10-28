from functools import wraps

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect

from apps.usuarios.perfis import url_painel_do_usuario

from .cookies import ACCESS_COOKIE, REFRESH_COOKIE, apagar_cookies, definir_access
from .tokens import ACCESS, REFRESH, TokenInvalido, decodificar


def usuario_do_token(token, tipo):
    """Devolve o usuário ativo e aprovado dono do token, ou None."""
    try:
        payload = decodificar(token, tipo)
    except TokenInvalido:
        return None
    Usuario = get_user_model()
    return Usuario.objects.filter(
        pk=payload['sub'], is_active=True, status_conta=Usuario.StatusConta.APROVADO,
    ).first()


def jwt_obrigatorio(view):
    """API: exige `Authorization: Bearer <access>` e preenche `request.user`."""

    @wraps(view)
    def _view(request, *args, **kwargs):
        esquema, _, token = request.headers.get('Authorization', '').partition(' ')
        if esquema.lower() != 'bearer' or not token:
            return JsonResponse({'erro': 'Token de acesso ausente.'}, status=401)
        usuario = usuario_do_token(token, ACCESS)
        if usuario is None:
            return JsonResponse({'erro': 'Token inválido ou expirado.'}, status=401)
        request.user = usuario
        return view(request, *args, **kwargs)

    return _view


def login_obrigatorio(*perfis):
    """Páginas: exige login via cookie JWT e, opcionalmente, um dos `perfis`.

    Com o access expirado, usa o refresh para emitir um novo access. Sem login
    válido, volta para a seleção de perfil; com perfil errado, vai para o
    painel do próprio usuário.
    """

    def decorador(view):
        @wraps(view)
        def _view(request, *args, **kwargs):
            usuario = usuario_do_token(request.COOKIES.get(ACCESS_COOKIE, ''), ACCESS)
            renovado = False
            if usuario is None:
                usuario = usuario_do_token(request.COOKIES.get(REFRESH_COOKIE, ''), REFRESH)
                renovado = usuario is not None
            if usuario is None:
                resposta = redirect('usuarios:index')
                apagar_cookies(resposta)
                return resposta
            if perfis and usuario.tipo_perfil not in perfis:
                return redirect(url_painel_do_usuario(usuario))

            request.user = usuario
            resposta = view(request, *args, **kwargs)
            if renovado:
                definir_access(resposta, usuario)
            return resposta

        return _view

    return decorador
