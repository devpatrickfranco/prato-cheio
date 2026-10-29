from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _criar(self, email, password, **campos):
        if not email:
            raise ValueError('O e-mail é obrigatório.')
        usuario = self.model(email=self.normalize_email(email), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **campos):
        campos.setdefault('is_staff', False)
        campos.setdefault('is_superuser', False)
        return self._criar(email, password, **campos)

    def create_superuser(self, email, password=None, **campos):
        campos.update(
            is_staff=True,
            is_superuser=True,
            tipo_perfil=Usuario.TipoPerfil.ADMIN,
            status_conta=Usuario.StatusConta.APROVADO,
        )
        return self._criar(email, password, **campos)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Credenciais e perfil de todos os atores do sistema.

    O login é feito pelo e-mail. `status_conta` sustenta o fluxo de aprovação
    feito pelo administrador; a senha fica no campo `password` (hash) herdado
    de AbstractBaseUser.
    """

    class TipoPerfil(models.TextChoices):
        DOADOR = 'doador', 'Doador'
        CONSUMIDOR = 'consumidor', 'Consumidor'  # pessoa física
        ONG = 'ong', 'ONG'  # pessoa jurídica
        ADMIN = 'admin', 'Administrador'

    class StatusConta(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        APROVADO = 'aprovado', 'Aprovado'
        RECUSADO = 'recusado', 'Recusado'

    nome = models.CharField(max_length=120)
    email = models.EmailField(max_length=150, unique=True)
    telefone = models.CharField(max_length=20, blank=True)
    # CPF (consumidor) ou CNPJ (ONG), somente números. O doador guarda o CNPJ em Estabelecimento.
    documento = models.CharField(max_length=14, blank=True, help_text='CPF ou CNPJ, somente números.')
    tipo_perfil = models.CharField(max_length=10, choices=TipoPerfil.choices)
    status_conta = models.CharField(max_length=10, choices=StatusConta.choices, default=StatusConta.PENDENTE)
    # Ponto de referência do consumidor/ONG para calcular a distância até os estabelecimentos.
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    class Meta:
        db_table = 'usuario'
        verbose_name = 'usuário'
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_perfil', 'documento'], condition=~models.Q(documento=''), name='uk_usuario_documento',
            ),
        ]

    def __str__(self):
        return self.nome

    @property
    def iniciais(self):
        partes = self.nome.split()
        return ''.join(parte[0] for parte in partes[:2]).upper()

    @property
    def coordenadas(self):
        if self.latitude is None or self.longitude is None:
            return None
        return float(self.latitude), float(self.longitude)


class Estabelecimento(models.Model):
    """Dados exclusivos do perfil doador (relação 1:1 com Usuario).

    O `bairro` alimenta o filtro de localização da vitrine.
    """

    class Tipo(models.TextChoices):
        MERCADO = 'mercado', 'Mercado'
        PADARIA = 'padaria', 'Padaria'
        HORTIFRUTI = 'hortifruti', 'Hortifruti'
        RESTAURANTE = 'restaurante', 'Restaurante'
        OUTRO = 'outro', 'Outro'

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='estabelecimento')
    razao_social = models.CharField(max_length=150)
    cnpj = models.CharField('CNPJ', max_length=14, unique=True, help_text='Somente números.')
    tipo_estabelecimento = models.CharField(max_length=12, choices=Tipo.choices)
    cep = models.CharField('CEP', max_length=8, help_text='Somente números.')
    logradouro = models.CharField(max_length=150)
    numero = models.CharField('número', max_length=10)
    bairro = models.CharField(max_length=80)
    cidade = models.CharField(max_length=80)
    uf = models.CharField('UF', max_length=2)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        db_table = 'estabelecimento'
        indexes = [models.Index(fields=['cidade', 'bairro'], name='idx_estab_bairro')]

    def __str__(self):
        return self.razao_social

    @property
    def coordenadas(self):
        if self.latitude is None or self.longitude is None:
            return None
        return float(self.latitude), float(self.longitude)
