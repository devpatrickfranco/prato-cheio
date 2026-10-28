import json

from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.usuarios.perfis import PERFIS

from .cookies import apagar_cookies, definir_cookies
from .decorators import jwt_obrigatorio, usuario_do_token
from .tokens import REFRESH, emitir_access, emitir_tokens


def _autenticar(request, email, senha):
    """Devolve (usuario, erro, status HTTP do erro); sem erro, erro é None."""
    usuario = authenticate(request, email=email, password=senha)
    if usuario is None:
        return None, 'E-mail ou senha inválidos.', 401
    if usuario.status_conta != usuario.StatusConta.APROVADO:
        return None, 'Sua conta ainda não foi aprovada.', 403
    return usuario, None, None


# Páginas web: o JWT viaja em cookies HttpOnly.

def login(request, perfil):
    perfil = PERFIS[perfil]
    contexto = {'perfil': perfil}
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        usuario, erro, _ = _autenticar(request, email, request.POST.get('senha', ''))
        if usuario is not None and usuario.tipo_perfil != perfil.slug:
            usuario, erro = None, f'Esta conta não é de {perfil.nome}. Use o acesso do seu perfil.'
        if usuario is not None:
            resposta = redirect(perfil.url_painel)
            definir_cookies(resposta, usuario)
            return resposta
        contexto.update(erro=erro, email=email)
    return render(request, 'jwt_auth/login.html', contexto)


@require_POST
def sair(request):
    resposta = redirect('usuarios:index')
    apagar_cookies(resposta)
    return resposta


# API JSON: autenticada por cabeçalho Bearer, não por cookie, por isso
# dispensa a verificação de CSRF.

def _dados(request):
    """Aceita corpo JSON ou formulário; devolve None se o JSON for inválido."""
    if request.content_type == 'application/json':
        try:
            return json.loads(request.body or b'{}')
        except ValueError:
            return None
    return request.POST


@csrf_exempt
@require_POST
def obter_token(request):
    dados = _dados(request)
    if dados is None:
        return JsonResponse({'erro': 'JSON inválido.'}, status=400)
    email, senha = dados.get('email'), dados.get('senha')
    if not email or not senha:
        return JsonResponse({'erro': 'Informe e-mail e senha.'}, status=400)

    usuario, erro, status = _autenticar(request, email, senha)
    if usuario is None:
        return JsonResponse({'erro': erro}, status=status)
    return JsonResponse(emitir_tokens(usuario))


@csrf_exempt
@require_POST
def renovar_token(request):
    dados = _dados(request)
    if dados is None:
        return JsonResponse({'erro': 'JSON inválido.'}, status=400)
    usuario = usuario_do_token(dados.get('refresh') or '', REFRESH)
    if usuario is None:
        return JsonResponse({'erro': 'Token de renovação inválido ou expirado.'}, status=401)
    return JsonResponse({'access': emitir_access(usuario)})


@require_GET
@jwt_obrigatorio
def usuario_atual(request):
    usuario = request.user
    return JsonResponse({
        'id': usuario.pk,
        'nome': usuario.nome,
        'email': usuario.email,
        'tipo_perfil': usuario.tipo_perfil,
    })
