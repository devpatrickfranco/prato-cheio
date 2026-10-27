from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Estabelecimento, Usuario


class UsuarioCriacaoForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('email', 'nome', 'tipo_perfil', 'status_conta')


class UsuarioEdicaoForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = '__all__'


class EstabelecimentoInline(admin.StackedInline):
    model = Estabelecimento
    extra = 0


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioEdicaoForm
    add_form = UsuarioCriacaoForm
    inlines = [EstabelecimentoInline]
    ordering = ('nome',)
    list_display = ('nome', 'email', 'tipo_perfil', 'status_conta', 'criado_em')
    list_filter = ('tipo_perfil', 'status_conta', 'is_active')
    search_fields = ('nome', 'email', 'estabelecimento__cnpj')
    actions = ['aprovar_contas', 'recusar_contas']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados', {'fields': ('nome', 'telefone', 'tipo_perfil', 'status_conta')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas', {'fields': ('last_login', 'criado_em')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'tipo_perfil', 'status_conta', 'password1', 'password2'),
        }),
    )

    @admin.action(description='Aprovar contas selecionadas')
    def aprovar_contas(self, request, queryset):
        total = queryset.update(status_conta=Usuario.Status.APROVADO)
        self.message_user(request, f'{total} conta(s) aprovada(s).')

    @admin.action(description='Recusar contas selecionadas')
    def recusar_contas(self, request, queryset):
        total = queryset.update(status_conta=Usuario.Status.RECUSADO)
        self.message_user(request, f'{total} conta(s) recusada(s).')


@admin.register(Estabelecimento)
class EstabelecimentoAdmin(admin.ModelAdmin):
    list_display = ('razao_social', 'cnpj', 'tipo_estabelecimento', 'bairro', 'cidade', 'uf')
    list_filter = ('tipo_estabelecimento', 'uf')
    search_fields = ('razao_social', 'cnpj', 'bairro', 'cidade')
