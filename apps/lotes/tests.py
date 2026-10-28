from datetime import timedelta
from decimal import Decimal
from io import StringIO
from math import pi

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.auth.cookies import ACCESS_COOKIE
from apps.auth.tokens import emitir_access
from apps.usuarios.models import Estabelecimento

from .catalogo import CATEGORIAS, categoria_do_alimento
from .geo import RAIO_TERRA_KM, caixa_delimitadora, haversine_km
from .models import Alimento, Categoria, Lote, Reserva
from .selectors import lotes_na_vitrine

BOSQUE = (-22.9096, -47.0626)
CENTRO = (-22.9056, -47.0608)
BARAO_GERALDO = (-22.8241, -47.0789)
SAO_PAULO = (-23.5505, -46.6333)


class HaversineTests(SimpleTestCase):
    def test_um_grau_no_equador(self):
        self.assertAlmostEqual(haversine_km((0, 0), (0, 1)), 2 * pi * RAIO_TERRA_KM / 360, places=6)

    def test_mesmo_ponto_e_simetria(self):
        self.assertEqual(haversine_km(CENTRO, CENTRO), 0)
        self.assertAlmostEqual(haversine_km(CENTRO, SAO_PAULO), haversine_km(SAO_PAULO, CENTRO))

    def test_campinas_ate_sao_paulo(self):
        self.assertAlmostEqual(haversine_km(CENTRO, SAO_PAULO), 83.4, delta=1)

    def test_caixa_contem_o_circulo(self):
        (lat_min, lat_max), (lon_min, lon_max) = caixa_delimitadora(CENTRO, 10)
        for destino in ((CENTRO[0] + 0.0899, CENTRO[1]), (CENTRO[0], CENTRO[1] + 0.0975)):
            self.assertLessEqual(haversine_km(CENTRO, destino), 10)
            self.assertTrue(lat_min <= destino[0] <= lat_max and lon_min <= destino[1] <= lon_max)


class CatalogoTests(TestCase):
    def test_classificacao_por_grupo_e_por_nome(self):
        casos = [
            ('cereais e leguminosas', 'arroz integral', 'Grãos e cereais'),
            ('aves e ovos', 'ovo de galinha', 'Ovos'),
            ('aves e ovos', 'peito de galinha ou frango', 'Carnes e aves'),
            ('açúcares e produtos de confeitaria', 'ovo de pascoa', 'Doces'),
            ('miscelâneas', 'suco de laranja', 'Bebidas'),
            ('miscelâneas', 'café da manhã', 'Pronto'),
            ('miscelâneas', 'pizza', 'Pronto'),
            ('grupo desconhecido', 'qualquer item', 'Pronto'),
        ]
        for grupo, descricao, categoria in casos:
            with self.subTest(descricao=descricao):
                self.assertEqual(categoria_do_alimento(grupo, descricao), categoria)

    def test_csv_carregado_e_todo_item_tem_categoria(self):
        self.assertEqual(Alimento.objects.count(), 1971)
        self.assertEqual(set(Categoria.objects.values_list('nome', flat=True)), set(CATEGORIAS))
        self.assertFalse(Alimento.objects.filter(categoria__isnull=True).exists())

        arroz = Alimento.objects.get(cod_pof=6300201, cod_preparo=99)
        self.assertEqual(arroz.descricao, 'arroz integral')
        self.assertEqual(arroz.categoria.nome, 'Grãos e cereais')
        self.assertEqual(arroz.cf_kgco2eq_por_kg, Decimal('1.07'))

    def test_fator_da_categoria_vem_dos_dados(self):
        hortifruti = Categoria.objects.get(nome='Hortifruti').fator_co2_kg
        carnes = Categoria.objects.get(nome='Carnes e aves').fator_co2_kg

        self.assertGreater(carnes, hortifruti)
        self.assertFalse(Categoria.objects.filter(fator_co2_kg=Decimal('2.50')).exists())


def _criar_estabelecimento(email, coordenadas, cnpj):
    Usuario = get_user_model()
    doador = Usuario.objects.create_user(
        email=email, password='x', nome=email, tipo_perfil='doador', status_conta='aprovado',
    )
    lat, lon = coordenadas if coordenadas else (None, None)
    return Estabelecimento.objects.create(
        usuario=doador, razao_social=email, cnpj=cnpj, tipo_estabelecimento='mercado', cep='13010100',
        logradouro='Rua A', numero='1', bairro='Centro', cidade='Campinas', uf='SP', latitude=lat, longitude=lon,
    )


def _criar_lote(estabelecimento, descricao, dias=0, status=Lote.Status.DISPONIVEL):
    agora = timezone.now()
    return Lote.objects.create(
        estabelecimento=estabelecimento, alimento=Alimento.objects.get(cod_pof=6705101, cod_preparo=99),
        descricao=descricao, quantidade=Decimal('15'), unidade='kg', peso_kg=Decimal('15'),
        data_validade=timezone.localdate() + timedelta(days=dias), status=status,
        retirada_inicio=agora, retirada_fim=agora + timedelta(hours=2),
    )


class ModelosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.receptor = get_user_model().objects.create_user(email='ong@exemplo.com', password='x', nome='ONG', tipo_perfil='ong')
        cls.lote = _criar_lote(_criar_estabelecimento('m@x.com', CENTRO, '11222333000181'), 'Kit hortifruti')

    def test_categoria_e_fator_vem_do_alimento(self):
        self.assertEqual(self.lote.categoria.nome, 'Hortifruti')
        self.assertEqual(self.lote.fator_co2_kg, Decimal('0.82'))
        self.assertEqual(self.lote.co2_evitado_kg, Decimal('12.30'))

    def test_lote_so_aceita_uma_reserva_ativa(self):
        expira = timezone.now() + timedelta(hours=1)
        Reserva.objects.create(lote=self.lote, usuario=self.receptor, data_expiracao=expira)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Reserva.objects.create(lote=self.lote, usuario=self.receptor, data_expiracao=expira)

        Reserva.objects.create(lote=self.lote, usuario=self.receptor, data_expiracao=expira, status='cancelada')

    def test_janela_de_retirada_invalida_e_rejeitada(self):
        self.lote.retirada_fim = self.lote.retirada_inicio

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.lote.save()


class VitrineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        centro = _criar_estabelecimento('centro@x.com', CENTRO, '11222333000181')
        barao = _criar_estabelecimento('barao@x.com', BARAO_GERALDO, '22333444000172')
        sem_local = _criar_estabelecimento('semlocal@x.com', None, '33444555000163')
        cls.perto = _criar_lote(centro, 'Lote perto', dias=1)
        cls.longe = _criar_lote(barao, 'Lote longe', dias=0)
        cls.sem_local = _criar_lote(sem_local, 'Lote sem local', dias=2)
        _criar_lote(centro, 'Lote vencido', dias=-1)
        _criar_lote(centro, 'Lote reservado', status=Lote.Status.RESERVADO)

        Usuario = get_user_model()
        cls.consumidor = Usuario.objects.create_user(
            email='joao@x.com', password='x', nome='João Silva', tipo_perfil='consumidor',
            status_conta='aprovado', latitude=Decimal(str(BOSQUE[0])), longitude=Decimal(str(BOSQUE[1])),
        )
        cls.ong_sem_local = Usuario.objects.create_user(
            email='ong@x.com', password='x', nome='ONG', tipo_perfil='ong', status_conta='aprovado',
        )

    def test_so_disponiveis_e_dentro_da_validade_ordenados_por_vencimento(self):
        descricoes = [lote.descricao for lote in lotes_na_vitrine()]

        self.assertEqual(descricoes, ['Lote longe', 'Lote perto', 'Lote sem local'])

    def test_distancia_calculada_por_lote(self):
        distancias = {lote.descricao: lote.distancia_km for lote in lotes_na_vitrine(BOSQUE)}

        self.assertAlmostEqual(distancias['Lote perto'], haversine_km(BOSQUE, CENTRO))
        self.assertLess(distancias['Lote perto'], 1)
        self.assertGreater(distancias['Lote longe'], 9)
        self.assertIsNone(distancias['Lote sem local'])

    def test_raio_maximo(self):
        self.assertEqual([lote.descricao for lote in lotes_na_vitrine(BOSQUE, 2)], ['Lote perto'])
        self.assertEqual(len(lotes_na_vitrine(BOSQUE, 50)), 2)

    def test_pagina_usa_localizacao_do_cadastro_e_filtra_raio(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.consumidor)

        resposta = self.client.get(reverse('lotes:explorar'), {'raio': '2'})

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Lote perto')
        self.assertNotContains(resposta, 'Lote longe')
        self.assertContains(resposta, 'km de você')

    def test_localizacao_do_navegador_tem_prioridade(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.consumidor)

        resposta = self.client.get(reverse('lotes:explorar'), {'raio': '2', 'lat': BARAO_GERALDO[0], 'lon': BARAO_GERALDO[1]})

        self.assertContains(resposta, 'Lote longe')
        self.assertNotContains(resposta, 'Lote perto')

    def test_sem_localizacao_lista_tudo_sem_distancia(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.ong_sem_local)

        resposta = self.client.get(reverse('lotes:explorar'), {'raio': '2'})

        self.assertEqual(len(resposta.context['lotes']), 3)
        self.assertNotContains(resposta, 'km de você')
        self.assertContains(resposta, 'Use sua localização')


class MeusLotesTests(TestCase):
    def test_doador_ve_apenas_os_proprios_lotes(self):
        meu = _criar_estabelecimento('meu@x.com', CENTRO, '11222333000181')
        outro = _criar_estabelecimento('outro@x.com', CENTRO, '22333444000172')
        _criar_lote(meu, 'Meu lote')
        _criar_lote(outro, 'Lote de outro doador')
        self.client.cookies[ACCESS_COOKIE] = emitir_access(meu.usuario)

        resposta = self.client.get(reverse('lotes:meus_lotes'))

        self.assertContains(resposta, 'Meu lote')
        self.assertNotContains(resposta, 'Lote de outro doador')


class CadastroLoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.estabelecimento = _criar_estabelecimento('doador@x.com', CENTRO, '11222333000181')
        cls.tomate = Alimento.objects.get(cod_pof=6705101, cod_preparo=99)

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.estabelecimento.usuario)

    def _dados(self, **alteracoes):
        amanha = timezone.localdate() + timedelta(days=1)
        dados = {
            'alimento': self.tomate.pk, 'categoria': '', 'descricao': 'Tomates maduros',
            'quantidade': '12', 'unidade': 'kg', 'peso_kg': '',
            'data_validade': amanha.isoformat(),
            'retirada_inicio': f'{amanha.isoformat()}T09:00', 'retirada_fim': f'{amanha.isoformat()}T11:00',
        }
        dados.update(alteracoes)
        return dados

    def test_formulario_lista_alimentos_agrupados_por_categoria(self):
        resposta = self.client.get(reverse('lotes:novo_lote'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, '<optgroup label="Grãos e cereais">')
        self.assertContains(resposta, '>arroz integral</option>')

    def test_cria_lote_com_categoria_e_peso_derivados(self):
        resposta = self.client.post(reverse('lotes:novo_lote'), self._dados(), follow=True)

        self.assertRedirects(resposta, reverse('lotes:meus_lotes'))
        self.assertContains(resposta, 'Lote &quot;Tomates maduros&quot; anunciado.')
        lote = Lote.objects.get(descricao='Tomates maduros')
        self.assertEqual(lote.estabelecimento, self.estabelecimento)
        self.assertEqual(lote.categoria.nome, 'Hortifruti')
        self.assertEqual(lote.peso_kg, Decimal('12'))
        self.assertEqual(lote.status, Lote.Status.DISPONIVEL)

    def test_lote_criado_aparece_na_vitrine(self):
        self.client.post(reverse('lotes:novo_lote'), self._dados())

        self.assertIn('Tomates maduros', [lote.descricao for lote in lotes_na_vitrine()])

    def test_cria_lote_so_com_categoria(self):
        padaria = Categoria.objects.get(nome='Padaria')

        self.client.post(reverse('lotes:novo_lote'), self._dados(alimento='', categoria=padaria.pk, descricao='Pães'))

        self.assertEqual(Lote.objects.get(descricao='Pães').categoria, padaria)

    def test_validacoes(self):
        ontem = (timezone.localdate() - timedelta(days=1)).isoformat()
        casos = {
            'categoria': self._dados(alimento=''),
            'peso_kg': self._dados(unidade='un'),
            'quantidade': self._dados(quantidade='0'),
            'data_validade': self._dados(data_validade=ontem),
            'retirada_fim': self._dados(retirada_fim=self._dados()['retirada_inicio']),
        }
        for campo, dados in casos.items():
            with self.subTest(campo=campo):
                resposta = self.client.post(reverse('lotes:novo_lote'), dados)

                self.assertEqual(resposta.status_code, 200)
                self.assertIn(campo, resposta.context['form'].errors)
        self.assertFalse(Lote.objects.exists())

    def test_edita_o_proprio_lote(self):
        lote = _criar_lote(self.estabelecimento, 'Lote antigo')

        resposta = self.client.post(reverse('lotes:editar_lote', args=[lote.pk]), self._dados(descricao='Lote editado'))

        self.assertRedirects(resposta, reverse('lotes:meus_lotes'))
        lote.refresh_from_db()
        self.assertEqual(lote.descricao, 'Lote editado')

    def test_nao_edita_lote_de_outro_doador_nem_reservado(self):
        outro = _criar_lote(_criar_estabelecimento('outro@x.com', CENTRO, '22333444000172'), 'De outro')
        reservado = _criar_lote(self.estabelecimento, 'Reservado', status=Lote.Status.RESERVADO)

        self.assertEqual(self.client.get(reverse('lotes:editar_lote', args=[outro.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('lotes:editar_lote', args=[reservado.pk])).status_code, 404)

    def test_doador_sem_estabelecimento_e_avisado(self):
        doador = get_user_model().objects.create_user(
            email='novo@x.com', password='x', nome='Novo', tipo_perfil='doador', status_conta='aprovado',
        )
        self.client.cookies[ACCESS_COOKIE] = emitir_access(doador)

        resposta = self.client.get(reverse('lotes:novo_lote'), follow=True)

        self.assertContains(resposta, 'Cadastre os dados do seu estabelecimento')

    def test_somente_doador_acessa(self):
        consumidor = get_user_model().objects.create_user(
            email='c@x.com', password='x', nome='C', tipo_perfil='consumidor', status_conta='aprovado',
        )
        self.client.cookies[ACCESS_COOKIE] = emitir_access(consumidor)

        resposta = self.client.get(reverse('lotes:novo_lote'))

        self.assertRedirects(resposta, reverse('metricas:dashboard_consumidor'))


class DadosDemoTests(TestCase):
    def test_comando_e_idempotente(self):
        call_command('criar_dados_demo', stdout=StringIO())
        call_command('criar_dados_demo', stdout=StringIO())

        self.assertEqual(Lote.objects.count(), 3)
        self.assertEqual(get_user_model().objects.filter(email__endswith='@demo.com').count(), 5)


class EstaticosTests(SimpleTestCase):
    def test_recursos_do_app_existem(self):
        for caminho in [*Lote.IMAGENS_PADRAO.values(), 'lotes/js/localizacao.js']:
            with self.subTest(caminho=caminho):
                self.assertIsNotNone(finders.find(caminho))
