from decimal import Decimal

from django import forms
from django.utils import timezone

from core.forms import FormularioAcessivel

from .models import Lote

TAMANHO_MAXIMO_FOTO = 5 * 1024 * 1024  # 5 MB
FORMATO_DATA_HORA = '%Y-%m-%dT%H:%M'


def _validar_tamanho(arquivo):
    if arquivo and arquivo.size > TAMANHO_MAXIMO_FOTO:
        raise forms.ValidationError('A imagem deve ter no máximo 5 MB.')
    return arquivo


class LoteForm(FormularioAcessivel, forms.ModelForm):
    """Cadastro e edição de lote pelo estabelecimento doador."""

    retirada_inicio = forms.DateTimeField(
        label='Início da retirada',
        input_formats=[FORMATO_DATA_HORA],
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'}, format=FORMATO_DATA_HORA
        ),
    )
    retirada_fim = forms.DateTimeField(
        label='Fim da retirada',
        input_formats=[FORMATO_DATA_HORA],
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'}, format=FORMATO_DATA_HORA
        ),
    )

    class Meta:
        model = Lote
        fields = [
            'descricao', 'categoria', 'tipo', 'preco', 'quantidade', 'unidade', 'peso_kg',
            'data_validade', 'retirada_inicio', 'retirada_fim', 'foto', 'foto_validade',
        ]
        widgets = {
            'descricao': forms.TextInput(attrs={'placeholder': 'Ex.: Kit hortifruti (tomates e cenouras)'}),
            'data_validade': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'preco': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01', 'inputmode': 'decimal'}),
            'quantidade': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01', 'inputmode': 'decimal'}),
            'peso_kg': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01', 'inputmode': 'decimal'}),
            'foto': forms.ClearableFileInput(attrs={'accept': 'image/*', 'data-tamanho-max': TAMANHO_MAXIMO_FOTO}),
            'foto_validade': forms.ClearableFileInput(attrs={'accept': 'image/*', 'data-tamanho-max': TAMANHO_MAXIMO_FOTO}),
        }
        help_texts = {
            'preco': 'Obrigatório para venda. Em doações, deixe em branco.',
            'peso_kg': 'Em lotes por unidade, informe o peso estimado. Deixe em branco se a unidade for kg.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].empty_label = 'Selecione uma categoria'
        self.fields['peso_kg'].required = False
        self.fields['foto_validade'].required = not (self.instance and self.instance.foto_validade)

    def clean_foto(self):
        return _validar_tamanho(self.cleaned_data.get('foto'))

    def clean_foto_validade(self):
        return _validar_tamanho(self.cleaned_data.get('foto_validade'))

    def clean(self):
        dados = super().clean()

        validade = dados.get('data_validade')
        if validade and validade < timezone.localdate():
            self.add_error('data_validade', 'A data de validade não pode estar no passado.')

        inicio, fim = dados.get('retirada_inicio'), dados.get('retirada_fim')
        if inicio and fim and fim <= inicio:
            self.add_error('retirada_fim', 'O fim da retirada deve ser depois do início.')
        elif fim and fim <= timezone.now():
            self.add_error('retirada_fim', 'O fim da retirada deve estar no futuro.')
        if fim and validade and timezone.localtime(fim).date() > validade:
            self.add_error('retirada_fim', 'A retirada deve terminar até a data de validade.')

        tipo, preco = dados.get('tipo'), dados.get('preco')
        if tipo == Lote.Tipo.VENDA and not preco:
            self.add_error('preco', 'Informe o preço de um lote à venda.')
        if tipo == Lote.Tipo.DOACAO:
            dados['preco'] = None

        if not dados.get('peso_kg'):
            quantidade = dados.get('quantidade')
            if dados.get('unidade') == Lote.Unidade.KG and quantidade:
                dados['peso_kg'] = Decimal(quantidade)
            elif 'peso_kg' not in self.errors:
                self.add_error('peso_kg', 'Informe o peso estimado do lote em kg.')
        return dados
