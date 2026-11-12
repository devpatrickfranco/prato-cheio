from datetime import date, datetime
from decimal import Decimal

from django import forms
from django.conf import settings
from django.utils import timezone

from .catalogo import PREPAROS_DE_VAREJO
from .models import Alimento, Lote

_FORMATO_HORA = '%H:%M'


class LoteForm(forms.ModelForm):
    """Cadastro e edição de lote pelo doador.

    O alimento é opcional; quando escolhido, define a categoria. Lotes em kg
    podem omitir o peso, que passa a ser a própria quantidade; em unidades, ele
    é obrigatório. O preço só existe em lotes à venda. A retirada é informada
    como dias (datas ISO separadas por vírgula) mais um horário comum a todos.
    """

    retirada_dias = forms.CharField(
        label='Dias disponíveis',
        help_text='Clique em cada dia em que o lote poderá ser retirado.',
        error_messages={'required': 'Selecione ao menos um dia de retirada.'},
        widget=forms.TextInput(attrs={'data-calendario': 'true', 'placeholder': 'AAAA-MM-DD, AAAA-MM-DD'}),
    )
    retirada_hora_inicio = forms.TimeField(
        label='Das', widget=forms.TimeInput(attrs={'type': 'time'}, format=_FORMATO_HORA),
    )
    retirada_hora_fim = forms.TimeField(
        label='Até as', widget=forms.TimeInput(attrs={'type': 'time'}, format=_FORMATO_HORA),
    )

    class Meta:
        model = Lote
        fields = [
            'alimento', 'categoria', 'descricao', 'modalidade', 'preco', 'quantidade', 'unidade', 'peso_kg',
            'data_validade', 'retirada_dias', 'foto',
        ]
        labels = {
            'alimento': 'Alimento',
            'descricao': 'Descrição do lote',
            'modalidade': 'Doação ou venda',
            'preco': 'Preço (R$)',
            'data_validade': 'Validade',
            'foto': 'Foto do lote',
        }
        help_texts = {
            'alimento': 'Opcional. Define a categoria e o cálculo de CO₂ evitado.',
            'categoria': 'Obrigatória se nenhum alimento for escolhido.',
            'modalidade': 'Doações aparecem só para ONGs. Vendas aparecem para ONGs e consumidores.',
            'peso_kg': 'Obrigatório para lotes em un. Para lotes em kg, deixe em branco para usar a quantidade.',
            'foto': f'Opcional. JPG, PNG ou WebP de até {settings.FOTO_LOTE_MAX_MB} MB. Sem foto, a vitrine usa a imagem da categoria.',
        }
        widgets = {
            'alimento': forms.Select(attrs={'data-autocomplete': 'true'}),
            'foto': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
            'descricao': forms.TextInput(attrs={'placeholder': 'Ex.: Kit hortifruti (tomates e cenouras)'}),
            'preco': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'quantidade': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'peso_kg': forms.NumberInput(attrs={'min': '0.001', 'step': '0.001'}),
            'data_validade': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
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

        # Dias que já passaram não voltam ao formulário ao editar o lote.
        hoje = timezone.localdate()
        self.initial['retirada_dias'] = ','.join(
            dia.isoformat() for dia in self.instance.dias_de_retirada if dia >= hoje
        )
        if self.instance.pk:
            self.initial['retirada_hora_inicio'] = timezone.localtime(self.instance.retirada_inicio).time()
            self.initial['retirada_hora_fim'] = timezone.localtime(self.instance.retirada_fim).time()

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

    def clean_retirada_dias(self):
        textos = [texto.strip() for texto in self.cleaned_data['retirada_dias'].split(',') if texto.strip()]
        try:
            dias = sorted({date.fromisoformat(texto) for texto in textos})
        except ValueError:
            raise forms.ValidationError('Informe os dias de retirada no formato AAAA-MM-DD.') from None
        if not dias:
            raise forms.ValidationError('Selecione ao menos um dia de retirada.')
        if dias[0] < timezone.localdate():
            raise forms.ValidationError('Os dias de retirada não podem estar no passado.')
        return [dia.isoformat() for dia in dias]

    def clean(self):
        dados = super().clean()
        alimento = dados.get('alimento')
        if alimento:
            dados['categoria'] = alimento.categoria
        elif not dados.get('categoria'):
            self.add_error('categoria', 'Escolha um alimento ou uma categoria.')

        if dados.get('modalidade') == Lote.Modalidade.VENDA:
            preco = dados.get('preco')
            if preco is None and 'preco' not in self.errors:
                self.add_error('preco', 'Informe o preço de venda.')
            elif preco is not None and preco <= Decimal('0'):
                self.add_error('preco', 'Informe um preço maior que zero.')
        else:
            dados['preco'] = None

        peso = dados.get('peso_kg')
        if peso is None:
            if dados.get('unidade') == Lote.Unidade.KG and dados.get('quantidade'):
                dados['peso_kg'] = dados['quantidade']
            elif dados.get('unidade') == Lote.Unidade.UN and 'peso_kg' not in self.errors:
                self.add_error('peso_kg', 'Informe o peso total do lote em kg.')
        elif peso <= Decimal('0'):
            self.add_error('peso_kg', 'Informe um peso maior que zero.')

        self._definir_janela_de_retirada(dados)
        return dados

    def _definir_janela_de_retirada(self, dados):
        """Valida os dias e o horário e deriva `retirada_inicio` e `retirada_fim` do lote."""
        dias = dados.get('retirada_dias')
        hora_inicio, hora_fim = dados.get('retirada_hora_inicio'), dados.get('retirada_hora_fim')
        if hora_inicio and hora_fim and hora_fim <= hora_inicio:
            self.add_error('retirada_hora_fim', 'O horário final deve ser depois do inicial.')
            return
        if not dias:
            return
        primeiro, ultimo = date.fromisoformat(dias[0]), date.fromisoformat(dias[-1])
        validade = dados.get('data_validade')
        if validade and ultimo > validade:
            self.add_error('retirada_dias', 'Os dias de retirada devem ser até a data de validade.')
            return
        if not (hora_inicio and hora_fim):
            return
        fim = timezone.make_aware(datetime.combine(ultimo, hora_fim))
        if fim <= timezone.now():
            self.add_error('retirada_hora_fim', 'O horário de retirada do último dia já passou.')
            return
        self.instance.retirada_inicio = timezone.make_aware(datetime.combine(primeiro, hora_inicio))
        self.instance.retirada_fim = fim
