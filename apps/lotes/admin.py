from django.contrib import admin

from .models import Alimento, Categoria, Lote, Reserva


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'fator_co2_kg']


@admin.register(Alimento)
class AlimentoAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'preparo', 'categoria', 'grupo', 'cf_kgco2eq_por_kg']
    list_filter = ['categoria', 'grupo']
    search_fields = ['descricao']


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'estabelecimento', 'categoria', 'peso_kg', 'data_validade', 'status']
    list_filter = ['status', 'categoria']
    autocomplete_fields = ['alimento']


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['lote', 'usuario', 'status', 'data_reserva', 'data_expiracao']
    list_filter = ['status']
