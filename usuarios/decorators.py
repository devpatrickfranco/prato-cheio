from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache


def jwt_required(*perfis):
    """Exige usuario autenticado por JWT e, opcionalmente, um dos perfis informados.

    Uso: ``@jwt_required()`` (qualquer perfil) ou ``@jwt_required('pj')``.
    """

    def decorador(view):
        @wraps(view)
        @never_cache
        def interna(request, *args, **kwargs):
            usuario = getattr(request, 'usuario', None)
            if usuario is None:
                messages.info(request, 'Entre na sua conta para continuar.')
                return redirect('usuarios:index')
            if perfis and usuario.tipo_perfil not in perfis:
                messages.error(request, 'Seu perfil não tem acesso a essa página.')
                return redirect('metricas:painel')
            return view(request, *args, **kwargs)

        return interna

    return decorador
