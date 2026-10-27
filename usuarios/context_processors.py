def usuario_logado(request):
    """Disponibiliza o usuario autenticado por JWT nos templates como ``usuario``."""
    return {'usuario': getattr(request, 'usuario', None)}
