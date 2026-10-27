from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from .validators import validar_cep, validar_cnpj


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _criar(self, email, password, **extra):
        if not email:
            raise ValueError('O e-mail é obrigatório.')
        usuario = self.model(email=self.normalize_email(email).lower(), **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault('tipo_perfil', Usuario.Perfil.PF)
        extra.setdefault('status_conta', Usuario.Status.APROVADO)
        return self._criar(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('tipo_perfil', Usuario.Perfil.ADMIN)
        extra.setdefault('status_conta', Usuario.Status.APROVADO)
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self._criar(email, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Credenciais e perfil de todos os atores do sistema."""

    class Perfil(models.TextChoices):
        PF = 'pf', 'Consumidor'
        PJ = 'pj', 'Doador (mercado/varejo)'
        ONG = 'ong', 'Instituição / ONG'
        ADMIN = 'admin', 'Administrador'

    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        APROVADO = 'aprovado', 'Aprovado'
        RECUSADO = 'recusado', 'Recusado'

    nome = models.CharField('nome', max_length=120)
    email = models.EmailField('e-mail', max_length=150, unique=True)
    telefone = models.CharField('telefone', max_length=20, blank=True)
    tipo_perfil = models.CharField(
        'perfil', max_length=5, choices=Perfil.choices, default=Perfil.PF
    )
    status_conta = models.CharField(
        'status da conta', max_length=10, choices=Status.choices, default=Status.PENDENTE
    )
    criado_em = models.DateTimeField('criado em', default=timezone.now)
    is_active = models.BooleanField('ativo', default=True)
    is_staff = models.BooleanField('acesso ao admin', default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_perfil_display()})'

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def pode_entrar(self):
        return self.is_active and self.status_conta == self.Status.APROVADO

    @property
    def iniciais(self):
        partes = [p for p in self.nome.split() if p]
        if not partes:
            return '?'
        if len(partes) == 1:
            return partes[0][:2].upper()
        return (partes[0][0] + partes[-1][0]).upper()

    @property
    def eh_doador(self):
        return self.tipo_perfil == self.Perfil.PJ

    @property
    def recebe_doacao(self):
        return self.tipo_perfil == self.Perfil.ONG


class Estabelecimento(models.Model):
    """Dados da pessoa jurídica (PJ doador/vendedor ou ONG) e sua localização.

    O bairro/cidade registrado aqui alimenta o filtro de localização da vitrine.
    """

    class Tipo(models.TextChoices):
        MERCADO = 'mercado', 'Mercado'
        PADARIA = 'padaria', 'Padaria'
        HORTIFRUTI = 'hortifruti', 'Hortifruti'
        RESTAURANTE = 'restaurante', 'Restaurante'
        ONG = 'ong', 'Instituição / ONG'
        OUTRO = 'outro', 'Outro'

    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, related_name='estabelecimento'
    )
    razao_social = models.CharField('razão social', max_length=150)
    cnpj = models.CharField('CNPJ', max_length=14, unique=True, validators=[validar_cnpj])
    tipo_estabelecimento = models.CharField(
        'tipo', max_length=12, choices=Tipo.choices, default=Tipo.OUTRO
    )
    cep = models.CharField('CEP', max_length=8, validators=[validar_cep])
    logradouro = models.CharField('logradouro', max_length=150)
    numero = models.CharField('número', max_length=10)
    bairro = models.CharField('bairro', max_length=80)
    cidade = models.CharField('cidade', max_length=80)
    uf = models.CharField('UF', max_length=2)

    class Meta:
        verbose_name = 'estabelecimento'
        verbose_name_plural = 'estabelecimentos'
        indexes = [models.Index(fields=['cidade', 'bairro'], name='idx_estab_bairro')]

    def __str__(self):
        return self.usuario.nome

    @property
    def endereco(self):
        return f'{self.logradouro}, {self.numero} - {self.bairro}, {self.cidade}/{self.uf}'
