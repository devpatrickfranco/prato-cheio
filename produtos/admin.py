from django.contrib import admin

from .models import Categoria, Lote, Reserva


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'fator_co2_kg', 'descricao')
    search_fields = ('nome',)


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = (
        'descricao', 'estabelecimento', 'categoria', 'tipo', 'quantidade', 'unidade',
        'data_validade', 'status',
    )
    list_filter = ('status', 'tipo', 'categoria')
    search_fields = ('descricao', 'estabelecimento__razao_social')
    date_hierarchy = 'data_validade'


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('lote', 'usuario', 'status', 'valor', 'comissao', 'data_reserva')
    list_filter = ('status',)
    search_fields = ('lote__descricao', 'usuario__nome')
