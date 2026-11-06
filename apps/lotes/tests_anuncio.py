"""Anúncio de lotes: doação ou venda, preço, peso e dias de retirada."""
from datetime import datetime, time, timedelta
from decimal import Decimal
from importlib import import_module

from django.apps import apps as registro_de_apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.auth.cookies import ACCESS_COOKIE
from apps.auth.tokens import emitir_access

from . import services
from .models import Alimento, Lote
from .selectors import lotes_na_vitrine, opcoes_de_filtro
from .tests import CENTRO, _criar_estabelecimento, _criar_lote


def _usuario(email, perfil):
    return get_user_model().objects.create_user(
        email=email, password='x', nome=email.split('@')[0].title(), tipo_perfil=perfil, status_conta='aprovado',
    )


def _dia(dias):
    return timezone.localdate() + timedelta(days=dias)


class VisibilidadePorPerfilTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.estabelecimento = _criar_estabelecimento('doador@x.com', CENTRO, '11222333000181')
        cls.consumidor = _usuario('joao@x.com', 'consumidor')
        cls.ong = _usuario('ong@x.com', 'ong')
        cls.doacao = _criar_lote(cls.estabelecimento, 'Lote doado', dias=1, preco=None)
        cls.venda = _criar_lote(cls.estabelecimento, 'Lote vendido', dias=1, preco=Decimal('12.50'))

    def _vitrine(self, usuario):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(usuario)
        return self.client.get(reverse('lotes:explorar'))

    def test_doacao_aparece_so_para_ong(self):
        self.assertEqual({lote.descricao for lote in lotes_na_vitrine('ong')}, {'Lote doado', 'Lote vendido'})
        self.assertEqual({lote.descricao for lote in lotes_na_vitrine('consumidor')}, {'Lote vendido'})

    def test_vitrine_mostra_preco_ou_doacao(self):
        resposta = self._vitrine(self.ong)

        self.assertContains(resposta, 'R$ 12,50')
        self.assertContains(resposta, '<span class="modalidade">Doação</span>', html=True)

    def test_consumidor_nao_ve_doacao_na_vitrine(self):
        resposta = self._vitrine(self.consumidor)

        self.assertContains(resposta, 'Lote vendido')
        self.assertNotContains(resposta, 'Lote doado')

    def test_filtros_nao_revelam_doacoes_ao_consumidor(self):
        padaria = _criar_estabelecimento('p@x.com', CENTRO, '22333444000172')
        padaria.bairro = 'Cambuí'
        padaria.save()
        _criar_lote(padaria, 'Só doação', dias=1, preco=None)

        self.assertEqual(opcoes_de_filtro('consumidor')[1], ['Centro'])
        self.assertEqual(opcoes_de_filtro('ong')[1], ['Cambuí', 'Centro'])

    def test_consumidor_nao_reserva_doacao(self):
        with self.assertRaisesMessage(services.RegraDeNegocio, 'doação exclusiva para ONGs'):
            services.reservar_lote(self.consumidor, self.doacao.pk)

        self.doacao.refresh_from_db()
        self.assertEqual(self.doacao.status, Lote.Status.DISPONIVEL)

    def test_ong_reserva_doacao_e_venda(self):
        services.reservar_lote(self.ong, self.doacao.pk)
        services.reservar_lote(self.ong, self.venda.pk)

        self.assertEqual(self.ong.reservas.count(), 2)

    def test_consumidor_reserva_venda(self):
        self.assertEqual(services.reservar_lote(self.consumidor, self.venda.pk).lote, self.venda)

    def test_banco_rejeita_preco_incoerente(self):
        casos = {'doacao': Decimal('5'), 'venda': None}
        for modalidade, preco in casos.items():
            with self.subTest(modalidade=modalidade):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Lote.objects.filter(pk=self.venda.pk).update(modalidade=modalidade, preco=preco)


class FormularioDeAnuncioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.estabelecimento = _criar_estabelecimento('doador@x.com', CENTRO, '11222333000181')
        cls.tomate = Alimento.objects.get(cod_pof=6705101, cod_preparo=99)

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.estabelecimento.usuario)

    def _dados(self, **alteracoes):
        dados = {
            'alimento': self.tomate.pk, 'categoria': '', 'descricao': 'Tomates', 'modalidade': 'doacao', 'preco': '',
            'quantidade': '12', 'unidade': 'un', 'peso_kg': '2', 'data_validade': _dia(10).isoformat(),
            'retirada_dias': _dia(1).isoformat(), 'retirada_hora_inicio': '10:00', 'retirada_hora_fim': '18:00',
        }
        dados.update(alteracoes)
        return dados

    def _enviar(self, **alteracoes):
        return self.client.post(reverse('lotes:novo_lote'), self._dados(**alteracoes))

    def _assert_erro(self, campo, **alteracoes):
        resposta = self._enviar(**alteracoes)

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(campo, resposta.context['form'].errors)
        self.assertFalse(Lote.objects.exists())

    def test_tela_em_portugues_com_un_como_padrao(self):
        resposta = self.client.get(reverse('lotes:novo_lote'))
        form = resposta.context['form']

        self.assertNotContains(resposta, 'Select an option')
        self.assertIn('<option value="" selected>Selecione</option>', str(form['categoria']))
        self.assertIn('<option value="" selected>Selecione</option>', str(form['modalidade']))
        self.assertIn('<option value="un" selected>un</option>', str(form['unidade']))
        self.assertIn('<option value="kg">kg</option>', str(form['unidade']))

    def test_modalidade_e_obrigatoria(self):
        self._assert_erro('modalidade', modalidade='')

    def test_venda_exige_preco_positivo(self):
        self._assert_erro('preco', modalidade='venda')
        self._assert_erro('preco', modalidade='venda', preco='0')
        self._assert_erro('preco', modalidade='venda', preco='-1')
        self._assert_erro('preco', modalidade='venda', preco='abc')

    def test_venda_guarda_o_preco(self):
        self._enviar(modalidade='venda', preco='12.50')

        lote = Lote.objects.get()
        self.assertEqual((lote.modalidade, lote.preco), ('venda', Decimal('12.50')))
        self.assertEqual(lote.modalidade_resumo, 'R$ 12,50')

    def test_doacao_descarta_preco_enviado(self):
        self._enviar(modalidade='doacao', preco='12.50')

        self.assertIsNone(Lote.objects.get().preco)

    def test_peso_e_obrigatorio_em_unidades(self):
        self._assert_erro('peso_kg', unidade='un', peso_kg='')

    def test_peso_em_kg_usa_a_quantidade_quando_em_branco(self):
        self._enviar(unidade='kg', quantidade='7.5', peso_kg='')

        self.assertEqual(Lote.objects.get().peso_kg, Decimal('7.5'))

    def test_peso_aceita_tres_casas_decimais(self):
        self._enviar(peso_kg='1.255')

        self.assertEqual(Lote.objects.get().peso_kg, Decimal('1.255'))

    def test_peso_recusa_quatro_casas_decimais(self):
        self._assert_erro('peso_kg', peso_kg='1.2555')

    def test_retirada_em_varios_dias_no_mesmo_horario(self):
        dias = [_dia(5), _dia(1), _dia(3)]

        resposta = self._enviar(retirada_dias=','.join(dia.isoformat() for dia in dias))

        self.assertRedirects(resposta, reverse('lotes:meus_lotes'))
        lote = Lote.objects.get()
        self.assertEqual(lote.dias_de_retirada, sorted(dias))
        self.assertEqual(timezone.localtime(lote.retirada_inicio).date(), _dia(1))
        self.assertEqual(timezone.localtime(lote.retirada_inicio).time(), time(10))
        self.assertEqual(timezone.localtime(lote.retirada_fim).date(), _dia(5))
        self.assertEqual(timezone.localtime(lote.retirada_fim).time(), time(18))
        esperado = f'{_dia(1):%d/%m}, {_dia(3):%d/%m}, {_dia(5):%d/%m}, das 10:00 às 18:00'
        self.assertEqual(lote.retirada_resumo, esperado)

    def test_validacoes_da_retirada(self):
        casos = [
            ('retirada_dias', {'retirada_dias': ''}),
            ('retirada_dias', {'retirada_dias': ' , '}),
            ('retirada_dias', {'retirada_dias': 'amanhã'}),
            ('retirada_dias', {'retirada_dias': _dia(-1).isoformat()}),
            ('retirada_dias', {'retirada_dias': _dia(11).isoformat()}),
            ('retirada_hora_inicio', {'retirada_hora_inicio': ''}),
            ('retirada_hora_fim', {'retirada_hora_fim': ''}),
            ('retirada_hora_fim', {'retirada_hora_inicio': '18:00', 'retirada_hora_fim': '10:00'}),
            ('retirada_hora_fim', {'retirada_dias': _dia(0).isoformat(), 'retirada_hora_inicio': '00:00', 'retirada_hora_fim': '00:01'}),
        ]
        for campo, alteracoes in casos:
            with self.subTest(campo=campo, alteracoes=alteracoes):
                self._assert_erro(campo, **alteracoes)

    def test_editar_preenche_a_retirada_sem_dias_que_ja_passaram(self):
        lote = _criar_lote(self.estabelecimento, 'Lote', dias=5)
        inicio = timezone.make_aware(datetime.combine(_dia(-1), time(10)))
        Lote.objects.filter(pk=lote.pk).update(
            retirada_dias=[_dia(-1).isoformat(), _dia(2).isoformat()],
            retirada_inicio=inicio,
            retirada_fim=timezone.make_aware(datetime.combine(_dia(2), time(18))),
        )

        form = self.client.get(reverse('lotes:editar_lote', args=[lote.pk])).context['form']

        self.assertEqual(form['retirada_dias'].value(), _dia(2).isoformat())
        self.assertIn('value="10:00"', str(form['retirada_hora_inicio']))
        self.assertIn('value="18:00"', str(form['retirada_hora_fim']))

    def test_meus_lotes_mostra_o_tipo(self):
        _criar_lote(self.estabelecimento, 'Vendido', preco=Decimal('1250'))
        _criar_lote(self.estabelecimento, 'Doado', preco=None)

        resposta = self.client.get(reverse('lotes:meus_lotes'))

        self.assertContains(resposta, 'R$ 1.250,00')
        self.assertContains(resposta, '<td>Doação</td>', html=True)


class MigracaoDosDiasDeRetiradaTests(TestCase):
    def test_lotes_antigos_recebem_cada_dia_da_janela(self):
        migracao = import_module('apps.lotes.migrations.0005_modalidade_preco_dias_retirada')
        lote = _criar_lote(_criar_estabelecimento('d@x.com', CENTRO, '11222333000181'), 'Antigo', dias=5)
        Lote.objects.filter(pk=lote.pk).update(
            retirada_dias=[],
            retirada_inicio=timezone.make_aware(datetime.combine(_dia(1), time(22))),
            retirada_fim=timezone.make_aware(datetime.combine(_dia(3), time(23))),
        )

        migracao.preencher_dias_de_retirada(registro_de_apps, None)

        lote.refresh_from_db()
        self.assertEqual(lote.dias_de_retirada, [_dia(1), _dia(2), _dia(3)])
