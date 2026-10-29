from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin

from .models import Estabelecimento, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Administração das contas: aprovação de cadastros e troca de senha (botão no formulário)."""

    list_display = ['nome', 'email', 'tipo_perfil', 'status_conta', 'criado_em', 'is_active']
    list_filter = ['status_conta', 'tipo_perfil', 'is_active']
    search_fields = ['nome', 'email', 'documento']
    ordering = ['-criado_em']
    readonly_fields = ['criado_em', 'last_login']
    actions = ['aprovar_contas', 'recusar_contas']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados pessoais', {'fields': ('nome', 'telefone', 'documento', 'latitude', 'longitude')}),
        ('Conta', {'fields': ('tipo_perfil', 'status_conta', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas', {'fields': ('criado_em', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'tipo_perfil', 'status_conta', 'password1', 'password2'),
        }),
    )

    @admin.action(description='Aprovar contas selecionadas')
    def aprovar_contas(self, request, queryset):
        total = queryset.update(status_conta=Usuario.StatusConta.APROVADO)
        self.message_user(request, f'{total} conta(s) aprovada(s).', messages.SUCCESS)

    @admin.action(description='Recusar contas selecionadas')
    def recusar_contas(self, request, queryset):
        total = queryset.update(status_conta=Usuario.StatusConta.RECUSADO)
        self.message_user(request, f'{total} conta(s) recusada(s).', messages.WARNING)


@admin.register(Estabelecimento)
class EstabelecimentoAdmin(admin.ModelAdmin):
    list_display = ['razao_social', 'cnpj', 'tipo_estabelecimento', 'bairro', 'cidade']
    search_fields = ['razao_social', 'cnpj']
