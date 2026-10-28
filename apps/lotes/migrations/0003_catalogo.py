"""Carga inicial: categorias e catálogo de alimentos a partir do CSV de pegadas.

O fator de CO₂ de cada categoria é a mediana da pegada de carbono (kg CO₂eq/kg)
dos seus alimentos na forma de varejo (cru ou "não se aplica"); sem itens
nessa forma, usa todos os preparos.
"""
import csv
from decimal import Decimal
from pathlib import Path
from statistics import median

from django.db import migrations

from apps.lotes.catalogo import CATEGORIAS, PREPAROS_DE_VAREJO, categoria_do_alimento

ARQUIVO = Path(__file__).resolve().parent.parent / 'dados' / 'pegadas_alimentos_brasil.csv'


def carregar_catalogo(apps, schema_editor):
    Categoria = apps.get_model('lotes', 'Categoria')
    Alimento = apps.get_model('lotes', 'Alimento')

    categorias = {
        nome: Categoria.objects.create(nome=nome, descricao=descricao)
        for nome, descricao in CATEGORIAS.items()
    }

    # utf-8-sig: o arquivo de origem tem BOM.
    with ARQUIVO.open(encoding='utf-8-sig', newline='') as arquivo:
        alimentos = [
            Alimento(
                categoria=categorias[categoria_do_alimento(linha['grupo'], linha['descricao'])],
                grupo=linha['grupo'],
                cod_pof=int(linha['cod_pof']),
                descricao=linha['descricao'],
                cod_preparo=int(linha['cod_preparo']),
                preparo=linha['preparo'],
                cf_gco2eq_100g=Decimal(linha['cf_gco2eq_100g']),
                wf_litros_100g=Decimal(linha['wf_litros_100g']),
                ef_m2g_100g=Decimal(linha['ef_m2g_100g']),
                cf_kgco2eq_por_kg=Decimal(linha['cf_kgco2eq_por_kg']),
            )
            for linha in csv.DictReader(arquivo)
        ]
    Alimento.objects.bulk_create(alimentos, batch_size=500)

    for categoria in categorias.values():
        itens = [a for a in alimentos if a.categoria is categoria]
        varejo = [a for a in itens if a.cod_preparo in PREPAROS_DE_VAREJO] or itens
        if varejo:
            fator = Decimal(median(a.cf_kgco2eq_por_kg for a in varejo)).quantize(Decimal('0.01'))
            categoria.fator_co2_kg = max(fator, Decimal('0.01'))
            categoria.save(update_fields=['fator_co2_kg'])


def remover_catalogo(apps, schema_editor):
    apps.get_model('lotes', 'Alimento').objects.all().delete()
    apps.get_model('lotes', 'Categoria').objects.filter(nome__in=CATEGORIAS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('lotes', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(carregar_catalogo, remover_catalogo),
    ]
