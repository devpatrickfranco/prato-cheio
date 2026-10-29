from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.lotes.catalogo import CATEGORIAS, categoria_do_alimento
from apps.lotes.models import Alimento, Categoria, Lote


class Command(BaseCommand):
    help = (
        'Reclassifica os alimentos nas categorias conforme apps/lotes/catalogo.py (a migration '
        '0003_catalogo só classifica na criação do banco). Cria categorias novas e atualiza os lotes '
        'que usam um alimento reclassificado. Use --simular para ver o que mudaria.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Mostra as mudanças sem gravar.')

    @transaction.atomic
    def handle(self, *args, simular=False, **options):
        categorias = {c.nome: c for c in Categoria.objects.all()}
        for nome, descricao in CATEGORIAS.items():
            if nome not in categorias:
                categorias[nome] = Categoria(nome=nome, descricao=descricao)
                if not simular:
                    categorias[nome].save()
                self.stdout.write(f'Nova categoria: {nome}')

        movidos = Counter()
        for alimento in Alimento.objects.select_related('categoria'):
            nova = categoria_do_alimento(alimento.grupo, alimento.descricao)
            if alimento.categoria.nome == nova:
                continue
            movidos[f'{alimento.categoria.nome} -> {nova}'] += 1
            if not simular:
                alimento.categoria = categorias[nova]
                alimento.save(update_fields=['categoria'])

        lotes = 0
        if not simular:
            for lote in Lote.objects.filter(alimento__isnull=False).select_related('alimento'):
                if lote.categoria_id != lote.alimento.categoria_id:
                    lote.categoria_id = lote.alimento.categoria_id
                    lote.save(update_fields=['categoria'])
                    lotes += 1

        for caminho, quantidade in sorted(movidos.items()):
            self.stdout.write(f'  {caminho}: {quantidade}')
        verbo = 'seriam reclassificados' if simular else 'reclassificados'
        self.stdout.write(self.style.SUCCESS(f'{sum(movidos.values())} alimento(s) {verbo}; {lotes} lote(s) atualizado(s).'))
