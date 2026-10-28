from django.contrib import admin

from .models import Estabelecimento, Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email', 'tipo_perfil', 'status_conta', 'is_active']
    list_filter = ['tipo_perfil', 'status_conta', 'is_active']
    search_fields = ['nome', 'email']
    exclude = ['password']


@admin.register(Estabelecimento)
class EstabelecimentoAdmin(admin.ModelAdmin):
    list_display = ['razao_social', 'cnpj', 'tipo_estabelecimento', 'bairro', 'cidade']
    search_fields = ['razao_social', 'cnpj']
