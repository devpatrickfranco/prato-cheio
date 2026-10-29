from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.auth.limitador import JANELA
from apps.auth.models import TentativaLogin, TokenRevogado


class Command(BaseCommand):
    help = 'Apaga tokens revogados já expirados e tentativas de login fora da janela de bloqueio.'

    def handle(self, *args, **options):
        agora = timezone.now()
        tokens = TokenRevogado.objects.filter(expira_em__lt=agora).delete()[0]
        tentativas = TentativaLogin.objects.filter(criado_em__lt=agora - JANELA - timedelta(hours=1)).delete()[0]
        self.stdout.write(self.style.SUCCESS(f'{tokens} token(s) revogado(s) e {tentativas} tentativa(s) removidos.'))
