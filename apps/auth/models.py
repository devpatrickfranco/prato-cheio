from django.db import models


class TokenRevogado(models.Model):
    """Lista de revogação: tokens JWT (pelo `jti`) invalidados antes de expirar, como no logout.

    A linha só precisa existir até `expira_em`; depois disso o próprio token já é inválido
    (limpeza: `python manage.py limpar_auth`).
    """

    jti = models.CharField(max_length=32, unique=True)
    expira_em = models.DateTimeField(db_index=True)
    revogado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'token_revogado'


class TentativaLogin(models.Model):
    """Falha de autenticação, usada para limitar tentativas por e-mail e por IP (força bruta)."""

    email = models.EmailField(max_length=150, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tentativa_login'
        indexes = [
            models.Index(fields=['email', 'criado_em'], name='idx_tentativa_email'),
            models.Index(fields=['ip', 'criado_em'], name='idx_tentativa_ip'),
        ]
