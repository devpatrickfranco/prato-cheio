from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Estabelecimento
from .validators import validar_cep, validar_cnpj, validar_cpf


class CadastroUsuarioForm(forms.Form):
    """Dados de acesso de qualquer perfil.

    Consumidor informa CPF e ONG informa CNPJ; o doador informa o CNPJ no formulário do
    estabelecimento. Consumidor e ONG podem informar um CEP para calcular distâncias.
    """

    nome = forms.CharField(label='Nome completo', max_length=120)
    email = forms.EmailField(label='E-mail', max_length=150)
    telefone = forms.CharField(label='Telefone', max_length=20, required=False)
    documento = forms.CharField(label='Documento', max_length=18)
    cep = forms.CharField(label='CEP', max_length=9, required=False, help_text='Opcional. Usado para calcular a distância até os estabelecimentos.')
    senha = forms.CharField(label='Senha', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}), help_text='Mínimo de 8 caracteres.')
    confirmar_senha = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def __init__(self, *args, perfil, **kwargs):
        super().__init__(*args, **kwargs)
        self.perfil = perfil
        if perfil.slug == 'consumidor':
            self.fields['documento'].label = 'CPF'
            self.fields['documento'].widget.attrs['placeholder'] = '000.000.000-00'
        elif perfil.slug == 'ong':
            self.fields['nome'].label = 'Nome da instituição'
            self.fields['documento'].label = 'CNPJ'
            self.fields['documento'].widget.attrs['placeholder'] = '00.000.000/0000-00'
        else:  # doador: o CNPJ fica no estabelecimento; o nome é o do responsável
            self.fields['nome'].label = 'Nome do responsável'
            del self.fields['documento'], self.fields['cep']
        self.fields['telefone'].widget.attrs['autocomplete'] = 'tel'
        self.fields['email'].widget.attrs['autocomplete'] = 'email'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError('Já existe uma conta com este e-mail.')
        return email

    def clean_documento(self):
        validador = validar_cpf if self.perfil.slug == 'consumidor' else validar_cnpj
        numero = validador(self.cleaned_data['documento'])
        if get_user_model().objects.filter(tipo_perfil=self.perfil.slug, documento=numero).exists():
            raise ValidationError('Este documento já está cadastrado.')
        return numero

    def clean_cep(self):
        cep = self.cleaned_data['cep']
        return validar_cep(cep) if cep.strip() else ''

    def clean(self):
        dados = super().clean()
        senha, confirmar = dados.get('senha'), dados.get('confirmar_senha')
        if senha and confirmar and senha != confirmar:
            self.add_error('confirmar_senha', 'As senhas não conferem.')
        elif senha:
            usuario = get_user_model()(nome=dados.get('nome', ''), email=dados.get('email', ''))
            try:
                validate_password(senha, usuario)
            except ValidationError as erro:
                self.add_error('senha', erro)
        return dados


class EstabelecimentoForm(forms.ModelForm):
    """Cadastro e edição do estabelecimento pelo próprio doador."""

    # Aceitam a máscara digitada; os validadores devolvem só os dígitos que o model guarda.
    cnpj = forms.CharField(label='CNPJ', max_length=18)
    cep = forms.CharField(label='CEP', max_length=9)

    class Meta:
        model = Estabelecimento
        fields = [
            'razao_social', 'cnpj', 'tipo_estabelecimento', 'cep', 'logradouro', 'numero', 'bairro', 'cidade', 'uf',
        ]
        labels = {'razao_social': 'Razão social', 'tipo_estabelecimento': 'Tipo de estabelecimento', 'uf': 'UF'}
        widgets = {
            'uf': forms.TextInput(attrs={'maxlength': '2', 'style': 'text-transform: uppercase'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cnpj'].widget.attrs.update(placeholder='00.000.000/0000-00', inputmode='numeric')
        self.fields['cep'].widget.attrs.update(placeholder='00000-000', inputmode='numeric')

    def clean_cnpj(self):
        numero = validar_cnpj(self.cleaned_data['cnpj'])
        if Estabelecimento.objects.filter(cnpj=numero).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Este CNPJ já está cadastrado.')
        return numero

    def clean_cep(self):
        return validar_cep(self.cleaned_data['cep'])

    def clean_uf(self):
        uf = self.cleaned_data['uf'].strip().upper()
        if len(uf) != 2 or not uf.isalpha():
            raise ValidationError('Informe a sigla do estado com 2 letras.')
        return uf

    def endereco_mudou(self):
        """Compara os valores já normalizados (sem máscara) com os originais da instância."""
        campos = ('cep', 'logradouro', 'numero', 'bairro', 'cidade', 'uf')
        return any(str(self.cleaned_data.get(campo, '')) != str(self.initial.get(campo, '')) for campo in campos)

