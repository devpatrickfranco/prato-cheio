from decimal import Decimal

from django.db import migrations

# Fator único de 2,5 kg CO2e por kg: estimativa didática herdada do esquema SQL do grupo.
# Substituir por fatores específicos quando a base de dados de CO2 (PDF) for incorporada.
CATEGORIAS = [
    ('Hortifruti', 'Frutas, legumes e verduras'),
    ('Padaria', 'Pães, bolos e produtos de panificação'),
    ('Laticínio', 'Leite, queijos e derivados'),
    ('Não perecíveis', 'Enlatados, grãos e industrializados'),
    ('Pronto', 'Refeições prontas e preparadas'),
]


def criar_categorias(apps, schema_editor):
    Categoria = apps.get_model('produtos', 'Categoria')
    for nome, descricao in CATEGORIAS:
        Categoria.objects.get_or_create(
            nome=nome,
            defaults={'descricao': descricao, 'fator_co2_kg': Decimal('2.50')},
        )


def remover_categorias(apps, schema_editor):
    Categoria = apps.get_model('produtos', 'Categoria')
    Categoria.objects.filter(nome__in=[nome for nome, _ in CATEGORIAS], lotes__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('produtos', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(criar_categorias, remover_categorias),
    ]
