from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Categoria(models.Model):
    """Classificação dos alimentos com o fator de conversão de CO₂.

    O fator é a mediana da pegada de carbono dos alimentos da categoria no
    CSV de pegadas (ver migration 0002_catalogo); é usado quando o lote não
    indica um alimento específico. É uma tabela (e não choices) para que o
    fator possa ser ajustado sem alterar código.
    """

    nome = models.CharField(max_length=60, unique=True)
    descricao = models.CharField('descrição', max_length=200, blank=True)
    fator_co2_kg = models.DecimalField(
        'fator CO₂ (kg/kg)', max_digits=6, decimal_places=2, default=Decimal('2.50'),
        help_text='kg de CO₂ equivalente evitados por kg de alimento aproveitado.',
    )

    class Meta:
        db_table = 'categoria'
        constraints = [models.CheckConstraint(condition=Q(fator_co2_kg__gt=0), name='ck_categoria_fator')]

    def __str__(self):
        return self.nome


class Alimento(models.Model):
    """Catálogo de alimentos com as pegadas ambientais por forma de preparo.

    Fonte: dados/pegadas_alimentos_brasil.csv (códigos de alimento da POF/IBGE).
    A categoria é atribuída por apps.lotes.catalogo.categoria_do_alimento.
    """

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='alimentos')
    grupo = models.CharField('grupo na fonte', max_length=60)
    cod_pof = models.PositiveIntegerField('código POF')
    descricao = models.CharField('descrição', max_length=120)
    cod_preparo = models.PositiveSmallIntegerField('código do preparo')
    preparo = models.CharField(max_length=40)
    cf_gco2eq_100g = models.DecimalField('pegada de carbono (g CO₂eq/100 g)', max_digits=10, decimal_places=2)
    wf_litros_100g = models.DecimalField('pegada hídrica (L/100 g)', max_digits=10, decimal_places=2)
    ef_m2g_100g = models.DecimalField('pegada ecológica (m²g/100 g)', max_digits=10, decimal_places=2)
    cf_kgco2eq_por_kg = models.DecimalField('pegada de carbono (kg CO₂eq/kg)', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'alimento'
        ordering = ['descricao', 'cod_preparo']
        constraints = [
            models.UniqueConstraint(fields=['cod_pof', 'cod_preparo'], name='uk_alimento_preparo'),
        ]

    def __str__(self):
        return f'{self.descricao} ({self.preparo})'


class Lote(models.Model):
    """Excedente publicado por um estabelecimento.

    `quantidade` + `unidade` servem à exibição; `peso_kg` é o valor canônico
    usado pelas métricas. Regras:
    - a vitrine mostra apenas lotes `disponivel` com `data_validade` >= hoje,
      ordenados pela validade mais próxima;
    - lotes disponíveis que passam da validade viram `expirado`;
    - só lotes `retirado` contam para as métricas de impacto.

    `alimento` é opcional; quando informado, define a categoria e o fator de
    CO₂ usado no cálculo do impacto.
    """

    # Imagens de vitrine para lotes sem foto, por categoria.
    IMAGENS_PADRAO = {
        'Hortifruti': 'lotes/img/hortifruti.jpg',
        'Padaria': 'lotes/img/paes.jpg',
        'Laticínio': 'lotes/img/laticinios.jpg',
    }

    class Unidade(models.TextChoices):
        KG = 'kg', 'kg'
        UN = 'un', 'un'

    class Status(models.TextChoices):
        DISPONIVEL = 'disponivel', 'Disponível'
        RESERVADO = 'reservado', 'Reservado'
        RETIRADO = 'retirado', 'Retirado'
        NAO_RETIRADO = 'nao_retirado', 'Não retirado'
        EXPIRADO = 'expirado', 'Expirado'

    estabelecimento = models.ForeignKey('usuarios.Estabelecimento', on_delete=models.CASCADE, related_name='lotes')
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='lotes')
    alimento = models.ForeignKey(Alimento, on_delete=models.PROTECT, related_name='lotes', null=True, blank=True)
    descricao = models.CharField('descrição', max_length=200)
    quantidade = models.DecimalField(max_digits=8, decimal_places=2)
    unidade = models.CharField(max_length=2, choices=Unidade.choices)
    peso_kg = models.DecimalField('peso (kg)', max_digits=8, decimal_places=2)
    data_validade = models.DateField()
    retirada_inicio = models.DateTimeField()
    retirada_fim = models.DateTimeField()
    foto_url = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DISPONIVEL)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lote'
        indexes = [models.Index(fields=['status', 'data_validade'], name='idx_lote_vitrine')]
        constraints = [
            models.CheckConstraint(condition=Q(quantidade__gt=0), name='ck_lote_quantidade'),
            models.CheckConstraint(condition=Q(peso_kg__gt=0), name='ck_lote_peso'),
            models.CheckConstraint(condition=Q(retirada_fim__gt=F('retirada_inicio')), name='ck_lote_janela'),
        ]

    def __str__(self):
        return self.descricao

    def save(self, *args, **kwargs):
        if self.alimento_id and not self.categoria_id:
            self.categoria_id = self.alimento.categoria_id
        super().save(*args, **kwargs)

    @property
    def fator_co2_kg(self):
        return self.alimento.cf_kgco2eq_por_kg if self.alimento_id else self.categoria.fator_co2_kg

    @property
    def co2_evitado_kg(self):
        return self.peso_kg * self.fator_co2_kg

    @property
    def imagem_padrao(self):
        return self.IMAGENS_PADRAO.get(self.categoria.nome)


class Reserva(models.Model):
    """Vínculo entre um lote e o consumidor ou ONG que o reservou.

    Um lote aceita apenas uma reserva `ativa` por vez. Reservas ativas cuja
    `data_expiracao` passou viram `expirada` e o lote volta a `disponivel`.
    """

    class Status(models.TextChoices):
        ATIVA = 'ativa', 'Ativa'
        CONFIRMADA = 'confirmada', 'Confirmada'
        EXPIRADA = 'expirada', 'Expirada'
        CANCELADA = 'cancelada', 'Cancelada'

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='reservas')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservas')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ATIVA)
    data_reserva = models.DateTimeField(auto_now_add=True)
    data_expiracao = models.DateTimeField('data de expiração')
    data_confirmacao = models.DateTimeField('data de confirmação', null=True, blank=True)
    observacao = models.CharField('observação', max_length=200, blank=True)

    class Meta:
        db_table = 'reserva'
        indexes = [models.Index(fields=['usuario', 'status'], name='idx_reserva_usuario')]
        constraints = [
            models.UniqueConstraint(fields=['lote'], condition=Q(status='ativa'), name='uk_reserva_ativa'),
        ]

    def __str__(self):
        return f'Reserva #{self.pk} – {self.lote}'
