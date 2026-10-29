from decimal import Decimal

from django import forms
from django.conf import settings
from django.utils import timezone

from .catalogo import PREPAROS_DE_VAREJO
from .models import Alimento, Lote

_FORMATO_DATA_HORA = '%Y-%m-%dT%H:%M'


class LoteForm(forms.ModelForm):
    """Cadastro e edição de lote pelo doador.

    O alimento é opcional; quando escolhido, define a categoria. Lotes em kg
    podem omitir o peso, que passa a ser a própria quantidade.
    """

    class Meta:
        model = Lote
        fields = [
            'alimento', 'categoria', 'descricao', 'quantidade', 'unidade', 'peso_kg',
            'data_validade', 'retirada_inicio', 'retirada_fim', 'foto',
        ]
        labels = {
            'alimento': 'Alimento',
            'descricao': 'Descrição do lote',
            'data_validade': 'Validade',
            'retirada_inicio': 'Retirada a partir de',
            'retirada_fim': 'Retirada até',
            'foto': 'Foto do lote',
        }
        help_texts = {
            'alimento': 'Opcional. Define a categoria e o cálculo de CO₂ evitado.',
            'categoria': 'Obrigatória se nenhum alimento for escolhido.',
            'peso_kg': 'Para lotes em kg, deixe em branco para usar a quantidade.',
            'foto': 'Opcional. JPG, PNG ou WebP de até 5 MB. Sem foto, a vitrine usa a imagem da categoria.',
        }
        widgets = {
            'alimento': forms.Select(attrs={'data-autocomplete': 'true'}),
            'foto': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
            'descricao': forms.TextInput(attrs={'placeholder': 'Ex.: Kit hortifruti (tomates e cenouras)'}),
            'quantidade': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'peso_kg': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'data_validade': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'retirada_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format=_FORMATO_DATA_HORA),
            'retirada_fim': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format=_FORMATO_DATA_HORA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False
        self.fields['peso_kg'].required = False

        alimentos = (
            Alimento.objects
            .filter(cod_preparo__in=PREPAROS_DE_VAREJO)
            .select_related('categoria')
            .order_by('categoria__nome', 'descricao', 'cod_preparo')
        )
        grupos = {}
        for alimento in alimentos:
            rotulo = alimento.descricao if alimento.cod_preparo != 1 else f'{alimento.descricao} ({alimento.preparo})'
            grupos.setdefault(alimento.categoria.nome, []).append((alimento.pk, rotulo))
        campo = self.fields['alimento']
        campo.queryset = alimentos
        campo.choices = [('', 'Nenhum (escolher só a categoria)'), *grupos.items()]

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        # Só valida arquivos recém-enviados (UploadedFile tem content_type; FieldFile salvo não).
        if foto and hasattr(foto, 'content_type'):
            limite = settings.FOTO_LOTE_MAX_MB * 1024 * 1024
            if foto.size > limite:
                raise forms.ValidationError(f'A foto deve ter no máximo {settings.FOTO_LOTE_MAX_MB} MB.')
            if foto.content_type not in ('image/jpeg', 'image/png', 'image/webp'):
                raise forms.ValidationError('Envie uma imagem JPG, PNG ou WebP.')
        return foto

    def clean_quantidade(self):
        quantidade = self.cleaned_data['quantidade']
        if quantidade <= 0:
            raise forms.ValidationError('Informe uma quantidade maior que zero.')
        return quantidade

    def clean_data_validade(self):
        validade = self.cleaned_data['data_validade']
        if validade < timezone.localdate():
            raise forms.ValidationError('A validade não pode estar no passado.')
        return validade

    def clean(self):
        dados = super().clean()
        alimento = dados.get('alimento')
        if alimento:
            dados['categoria'] = alimento.categoria
        elif not dados.get('categoria'):
            self.add_error('categoria', 'Escolha um alimento ou uma categoria.')

        peso = dados.get('peso_kg')
        if peso is None:
            if dados.get('unidade') == Lote.Unidade.KG and dados.get('quantidade'):
                dados['peso_kg'] = dados['quantidade']
            elif dados.get('unidade') == Lote.Unidade.UN:
                self.add_error('peso_kg', 'Informe o peso total do lote em kg.')
        elif peso <= Decimal('0'):
            self.add_error('peso_kg', 'Informe um peso maior que zero.')

        inicio, fim = dados.get('retirada_inicio'), dados.get('retirada_fim')
        if inicio and fim:
            if fim <= inicio:
                self.add_error('retirada_fim', 'O fim da retirada deve ser depois do início.')
            validade = dados.get('data_validade')
            if validade and timezone.localtime(inicio).date() > validade:
                self.add_error('retirada_inicio', 'A retirada deve começar até a data de validade.')
        return dados
