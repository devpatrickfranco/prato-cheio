from django import forms
from django.contrib.auth.password_validation import validate_password

from core.forms import FormularioAcessivel

from .models import Estabelecimento, Usuario
from .validators import somente_digitos, validar_cnpj, validar_telefone

UF_CHOICES = [(uf, uf) for uf in (
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
    'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
)]


class LoginForm(FormularioAcessivel, forms.Form):
    email = forms.EmailField(
        label='E-mail',
        max_length=150,
        widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com', 'autocomplete': 'email'}),
    )
    senha = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )


class CadastroUsuarioForm(FormularioAcessivel, forms.ModelForm):
    """Dados de acesso, comuns a todos os perfis."""

    telefone = forms.CharField(
        label='Telefone com DDD',
        max_length=15,
        help_text='Usado para combinar a retirada.',
        widget=forms.TextInput(attrs={
            'type': 'tel',
            'autocomplete': 'tel',
            'inputmode': 'tel',
            'pattern': r'[0-9()\s\-+]{10,15}',
            'data-mensagem': 'Informe o telefone com DDD, por exemplo (19) 99999-0000.',
        }),
    )
    senha = forms.CharField(
        label='Senha',
        min_length=8,
        help_text='Mínimo de 8 caracteres.',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    confirmar_senha = forms.CharField(
        label='Confirme a senha',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'data-igual': 'id_senha'}),
    )

    class Meta:
        model = Usuario
        fields = ['nome', 'email']
        widgets = {
            'nome': forms.TextInput(attrs={'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'seu@email.com'}),
        }
        error_messages = {
            'email': {'unique': 'Já existe uma conta com este e-mail.'},
        }

    def __init__(self, *args, rotulo_nome='Nome completo', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].label = rotulo_nome

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_telefone(self):
        telefone = somente_digitos(self.cleaned_data['telefone'])
        validar_telefone(telefone)
        return telefone

    def clean(self):
        dados = super().clean()
        senha = dados.get('senha')
        if senha and senha != dados.get('confirmar_senha'):
            self.add_error('confirmar_senha', 'As senhas não coincidem.')
        elif senha:
            candidato = Usuario(nome=dados.get('nome', ''), email=dados.get('email', ''))
            try:
                validate_password(senha, user=candidato)
            except forms.ValidationError as erro:
                self.add_error('senha', erro)
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.telefone = self.cleaned_data['telefone']
        usuario.set_password(self.cleaned_data['senha'])
        if commit:
            usuario.save()
        return usuario


class EstabelecimentoForm(FormularioAcessivel, forms.ModelForm):
    """Dados da pessoa jurídica (PJ ou ONG), incluindo o endereço usado no filtro de bairro."""

    cnpj = forms.CharField(
        label='CNPJ',
        max_length=18,
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'pattern': r'[0-9./\-]{14,18}',
            'placeholder': '00.000.000/0000-00',
            'data-mensagem': 'Informe o CNPJ com 14 dígitos.',
        }),
    )
    cep = forms.CharField(
        label='CEP',
        max_length=9,
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'autocomplete': 'postal-code',
            'pattern': r'[0-9]{5}-?[0-9]{3}',
            'placeholder': '00000-000',
            'data-mensagem': 'Informe o CEP no formato 00000-000.',
        }),
    )
    uf = forms.ChoiceField(label='UF', choices=[('', 'Selecione')] + UF_CHOICES)

    class Meta:
        model = Estabelecimento
        fields = [
            'razao_social', 'cnpj', 'tipo_estabelecimento',
            'cep', 'logradouro', 'numero', 'bairro', 'cidade', 'uf',
        ]
        widgets = {
            'logradouro': forms.TextInput(attrs={'autocomplete': 'address-line1'}),
            'bairro': forms.TextInput(attrs={'autocomplete': 'address-level3'}),
            'cidade': forms.TextInput(attrs={'autocomplete': 'address-level2'}),
        }
        error_messages = {
            'cnpj': {'unique': 'Já existe um cadastro com este CNPJ.'},
        }

    def __init__(self, *args, perfil, **kwargs):
        super().__init__(*args, **kwargs)
        self.perfil = perfil
        self.fields['razao_social'].label = 'Razão social' if perfil == Usuario.Perfil.PJ else 'Nome da instituição'
        tipo = self.fields['tipo_estabelecimento']
        if perfil == Usuario.Perfil.ONG:
            # ONG nao escolhe o tipo: ele e sempre "ONG".
            del self.fields['tipo_estabelecimento']
        else:
            tipo.choices = [
                (valor, rotulo) for valor, rotulo in Estabelecimento.Tipo.choices
                if valor != Estabelecimento.Tipo.ONG
            ]

    def clean_cnpj(self):
        cnpj = somente_digitos(self.cleaned_data['cnpj'])
        validar_cnpj(cnpj)
        return cnpj

    def clean_cep(self):
        return somente_digitos(self.cleaned_data['cep'])

    def clean_uf(self):
        return self.cleaned_data['uf'].upper()

    def save(self, commit=True):
        estabelecimento = super().save(commit=False)
        if self.perfil == Usuario.Perfil.ONG:
            estabelecimento.tipo_estabelecimento = Estabelecimento.Tipo.ONG
        if commit:
            estabelecimento.save()
        return estabelecimento
