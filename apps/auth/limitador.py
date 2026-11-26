"""Limite de tentativas de login (proteção contra força bruta).

Cada senha errada grava uma `TentativaLogin`. Dentro da janela, o e-mail é bloqueado ao atingir
MAX_FALHAS_EMAIL falhas e o IP ao atingir MAX_FALHAS_IP. Um login correto zera as falhas do e-mail.
"""
import ipaddress
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import TentativaLogin

JANELA = timedelta(minutes=15)
MAX_FALHAS_EMAIL = 5
MAX_FALHAS_IP = 20
MENSAGEM = 'Muitas tentativas de login. Aguarde alguns minutos e tente novamente.'


def ip_do_cliente(request):
    """IP de origem. Atrás de proxy, defina DJANGO_PROXY_IP_HEADER (ex.: HTTP_X_FORWARDED_FOR).

    Cada proxy confiável acrescenta um valor ao fim do cabeçalho, então o IP do cliente é o N-ésimo a
    partir do fim, onde N é DJANGO_PROXIES_CONFIAVEIS (padrão 1). Os valores anteriores são controlados
    pelo cliente. Cabeçalho com menos valores que N, ou valor que não seja um IP, cai para REMOTE_ADDR.
    """
    cabecalho = settings.PROXY_IP_HEADER
    if cabecalho and request.META.get(cabecalho):
        valores = [valor.strip() for valor in request.META[cabecalho].split(',')]
        proxies = max(settings.PROXIES_CONFIAVEIS, 1)
        if len(valores) >= proxies:
            try:
                return str(ipaddress.ip_address(valores[-proxies]))
            except ValueError:
                pass
    return request.META.get('REMOTE_ADDR')


def _recentes():
    return TentativaLogin.objects.filter(criado_em__gte=timezone.now() - JANELA)


def bloqueado(request, email):
    email = (email or '').strip().lower()
    if email and _recentes().filter(email=email).count() >= MAX_FALHAS_EMAIL:
        return True
    ip = ip_do_cliente(request)
    return bool(ip) and _recentes().filter(ip=ip).count() >= MAX_FALHAS_IP


def registrar_falha(request, email):
    TentativaLogin.objects.create(email=(email or '').strip().lower(), ip=ip_do_cliente(request))


def limpar(email):
    TentativaLogin.objects.filter(email=(email or '').strip().lower()).delete()
