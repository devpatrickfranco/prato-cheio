from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from usuarios.models import Estabelecimento, Usuario


class Categoria(models.Model):
    """Classifica os alimentos e guarda o fator de conversão para CO2.

    Modelada como tabela (e não enum) para que o fator possa ser atualizado sem
    mexer no código, por exemplo quando a base de dados de CO2 em PDF for incorporada.
    """

    nome = models.CharField('nome', max_length=60, unique=True)
    descricao = models.CharField('descrição', max_length=200, blank=True)
    fator_co2_kg = models.DecimalField(
        'fator de CO₂ (kg CO₂e por kg)',
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Quilos de CO₂ equivalente evitados por quilo de alimento aproveitado.',
    )

    class Meta:
        verbose_name = 'categoria'
        verbose_name_plural = 'categorias'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Lote(models.Model):
    """Excedente publicado por um estabelecimento (para doação ou venda)."""

    class Unidade(models.TextChoices):
        KG = 'kg', 'kg'
        UN = 'un', 'un'

    class Tipo(models.TextChoices):
        DOACAO = 'doacao', 'Doação'
        VENDA = 'venda', 'Venda'

    class Status(models.TextChoices):
        DISPONIVEL = 'disponivel', 'Disponível'
        RESERVADO = 'reservado', 'Reservado'
        RETIRADO = 'retirado', 'Retirado'
        NAO_RETIRADO = 'nao_retirado', 'Não retirado'
        EXPIRADO = 'expirado', 'Expirado'

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.CASCADE, related_name='lotes'
    )
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='lotes')
    descricao = models.CharField('descrição', max_length=200)
    tipo = models.CharField('tipo', max_length=6, choices=Tipo.choices, default=Tipo.DOACAO)
    preco = models.DecimalField(
        'preço total (R$)', max_digits=8, decimal_places=2, null=True, blank=True
    )
    quantidade = models.DecimalField(
        'quantidade',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    unidade = models.CharField('unidade', max_length=2, choices=Unidade.choices, default=Unidade.KG)
    peso_kg = models.DecimalField(
        'peso total (kg)',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Base do cálculo de impacto. Em lotes por unidade, informe o peso estimado.',
    )
    data_validade = models.DateField('data de validade')
    retirada_inicio = models.DateTimeField('início da retirada')
    retirada_fim = models.DateTimeField('fim da retirada')
    foto = models.ImageField('foto do lote', upload_to='lotes/', blank=True)
    foto_validade = models.ImageField(
        'foto do código de barras e da validade',
        upload_to='lotes/validade/',
        blank=True,
        help_text='Garantia de qualidade: mostre o código de barras e a data de validade.',
    )
    status = models.CharField(
        'status', max_length=12, choices=Status.choices, default=Status.DISPONIVEL
    )
    criado_em = models.DateTimeField('publicado em', default=timezone.now)

    class Meta:
        verbose_name = 'lote'
        verbose_name_plural = 'lotes'
        ordering = ['data_validade', 'retirada_inicio']
        indexes = [
            models.Index(fields=['status', 'data_validade'], name='idx_lote_vitrine'),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(quantidade__gt=0), name='ck_lote_quantidade'),
            models.CheckConstraint(condition=Q(peso_kg__gt=0), name='ck_lote_peso'),
            models.CheckConstraint(
                condition=Q(retirada_fim__gt=models.F('retirada_inicio')), name='ck_lote_janela'
            ),
            models.CheckConstraint(
                condition=Q(tipo='doacao') | Q(preco__gt=0), name='ck_lote_preco_venda'
            ),
        ]

    def __str__(self):
        return f'{self.descricao} ({self.get_status_display()})'

    @property
    def eh_venda(self):
        return self.tipo == self.Tipo.VENDA

    @property
    def editavel(self):
        return self.status == self.Status.DISPONIVEL


class Reserva(models.Model):
    """Vincula quem vai retirar (ou comprar) a um lote."""

    class Status(models.TextChoices):
        ATIVA = 'ativa', 'Ativa'
        CONFIRMADA = 'confirmada', 'Confirmada'
        EXPIRADA = 'expirada', 'Expirada'
        CANCELADA = 'cancelada', 'Cancelada'

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='reservas')
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='reservas')
    status = models.CharField(
        'status', max_length=10, choices=Status.choices, default=Status.ATIVA
    )
    data_reserva = models.DateTimeField('reservado em', default=timezone.now)
    data_expiracao = models.DateTimeField('expira em')
    data_confirmacao = models.DateTimeField('retirada confirmada em', null=True, blank=True)
    observacao = models.CharField('observação', max_length=200, blank=True)
    valor = models.DecimalField('valor (R$)', max_digits=8, decimal_places=2, default=0)
    comissao = models.DecimalField(
        'comissão da plataforma (R$)', max_digits=8, decimal_places=2, default=0
    )

    class Meta:
        verbose_name = 'reserva'
        verbose_name_plural = 'reservas'
        ordering = ['-data_reserva']
        indexes = [
            models.Index(fields=['usuario', 'status'], name='idx_reserva_usuario'),
        ]
        constraints = [
            # Apenas uma reserva ativa por lote (regra garantida pelo banco).
            models.UniqueConstraint(
                fields=['lote'],
                condition=Q(status='ativa'),
                name='uk_reserva_ativa',
            ),
        ]

    def __str__(self):
        return f'Reserva de {self.usuario.nome} - {self.lote.descricao}'
