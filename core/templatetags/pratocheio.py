from decimal import Decimal

from django import template
from django.templatetags.static import static
from django.utils import timezone

register = template.Library()

# Imagem padrão exibida quando o lote não tem foto, conforme a categoria.
IMAGENS_CATEGORIA = {
    'hortifruti': 'usuarios/img/hortifruti.jpg',
    'padaria': 'usuarios/img/paes.jpg',
    'laticínio': 'usuarios/img/laticinios.jpg',
}


@register.filter
def dia_relativo(valor):
    """Data/hora curta: 'Hoje, 20:00', 'Amanhã, 10:00' ou '25/10, 08:00'."""
    if not valor:
        return ''
    if timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    hoje = timezone.localdate()
    dias = (valor.date() - hoje).days
    hora = valor.strftime('%H:%M')
    if dias == 0:
        return f'Hoje, {hora}'
    if dias == 1:
        return f'Amanhã, {hora}'
    return f'{valor:%d/%m}, {hora}'


@register.filter
def hora(valor):
    """Apenas HH:MM no fuso local."""
    if not valor:
        return ''
    if timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return valor.strftime('%H:%M')


@register.filter
def quantidade(lote):
    """'15kg' ou '20un', sem zeros desnecessários."""
    numero = lote.quantidade.normalize()
    texto = f'{numero:f}'.replace('.', ',')
    return f'{texto}{lote.unidade}'


@register.filter
def peso(valor):
    """Peso em kg; acima de 1000 kg mostra em toneladas."""
    valor = Decimal(valor or 0)
    if valor >= 1000:
        return f'{(valor / 1000):.1f}'.replace('.', ',') + ' t'
    return f'{valor:.1f}'.replace('.', ',') + ' kg'


@register.filter
def dinheiro(valor):
    """R$ 1.234,56"""
    valor = Decimal(valor or 0)
    texto = f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {texto}'


@register.filter
def imagem_padrao(categoria):
    """Caminho estático da imagem da categoria, ou vazio se não houver."""
    caminho = IMAGENS_CATEGORIA.get(categoria.nome.lower())
    return static(caminho) if caminho else ''


@register.filter
def sinal(valor):
    """'+12%' / '-5%'; None vira texto vazio."""
    if valor is None:
        return ''
    return f'{valor:+d}%'
