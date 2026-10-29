from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.auth.cookies import ACCESS_COOKIE
from apps.auth.tokens import emitir_access
from apps.lotes import services
from apps.lotes.models import Alimento, Lote, Reserva
from apps.lotes.tests import CENTRO, _criar_estabelecimento, _criar_lote

from . import servicos


class CalculoTests(SimpleTestCase):
    def test_variacao_mensal(self):
        self.assertEqual(servicos.variacao(Decimal('15'), Decimal('10')), '+50% este mês')
        self.assertEqual(servicos.variacao(Decimal('5'), Decimal('10')), '-50% este mês')
        self.assertEqual(servicos.variacao(Decimal('10'), Decimal('10')), '+0% este mês')
        self.assertEqual(servicos.variacao(Decimal('3'), Decimal('0')), 'Novo este mês')
        self.assertEqual(servicos.variacao(Decimal('0'), Decimal('0')), 'Sem retiradas este mês')

    def test_refeicoes_sao_kg_divididos_por_0_4(self):
        self.assertEqual(servicos.Totais(kg=Decimal('15')).refeicoes, Decimal('38'))

    def test_janela_de_meses_atravessa_o_ano(self):
        meses = servicos.totais_por_mes([], meses=4, hoje=timezone.make_aware(datetime(2027, 2, 10)))

        self.assertEqual(list(meses), [(2026, 11), (2026, 12), (2027, 1), (2027, 2)])
        self.assertEqual(servicos.rotulo_mes((2026, 11)), 'nov/26')


class PainelRealTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.estabelecimento = _criar_estabelecimento('doador@x.com', CENTRO, '11222333000181')
        cls.doador = cls.estabelecimento.usuario
        cls.consumidor = Usuario.objects.create_user(
            email='joao@x.com', password='x', nome='João Silva', tipo_perfil='consumidor', status_conta='aprovado',
        )
        cls.ong = Usuario.objects.create_user(
            email='ong@x.com', password='x', nome='Instituto Esperança', tipo_perfil='ong', status_conta='aprovado',
        )

    def _retirar(self, descricao, receptor, quando=None):
        """Lote de 15 kg de tomate (0,82 kg CO₂/kg = 12,30 kg) reservado e retirado."""
        lote = _criar_lote(self.estabelecimento, descricao, dias=1)
        services.reservar_lote(receptor, lote.pk)
        services.confirmar_retirada(self.doador, lote.pk)
        if quando:
            Reserva.objects.filter(lote=lote).update(data_confirmacao=quando)
        return lote

    def _painel(self, usuario, perfil):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(usuario)
        return self.client.get(reverse(f'metricas:dashboard_{perfil}'))

    def test_sem_retiradas_painel_zerado(self):
        resposta = self._painel(self.doador, 'doador')

        self.assertContains(resposta, 'Sem retiradas este mês')
        self.assertContains(resposta, 'Nenhuma retirada confirmada ainda')
        self.assertEqual([m['valor'] for m in resposta.context['metricas']], ['0,0', '0,0', '0'])

    def test_doador_soma_as_retiradas_confirmadas(self):
        self._retirar('Kit A', self.consumidor)
        self._retirar('Kit B', self.ong)

        resposta = self._painel(self.doador, 'doador')

        valores = [(m['valor'], m['unidade']) for m in resposta.context['metricas']]
        self.assertEqual(valores, [('24,6', 'kg'), ('30,0', 'kg'), ('75', '')])
        self.assertEqual([m['tendencia'] for m in resposta.context['metricas']], ['Novo este mês'] * 3)
        self.assertContains(resposta, 'João Silva retirou 15,0 kg: Kit A.')
        self.assertEqual(len(resposta.context['atividades']), 2)

    def test_so_retiradas_confirmadas_contam(self):
        lote = _criar_lote(self.estabelecimento, 'Só reservado', dias=1)
        services.reservar_lote(self.consumidor, lote.pk)
        outro = _criar_lote(self.estabelecimento, 'Não retirado', dias=1)
        services.reservar_lote(self.ong, outro.pk)
        services.registrar_nao_retirada(self.doador, outro.pk)

        resposta = self._painel(self.doador, 'doador')

        self.assertEqual(resposta.context['metricas'][1]['valor'], '0,0')

    def test_consumidor_ve_so_o_que_ele_retirou(self):
        self._retirar('Kit A', self.consumidor)
        self._retirar('Kit B', self.ong)

        consumidor = self._painel(self.consumidor, 'consumidor')
        ong = self._painel(self.ong, 'ong')

        self.assertEqual(consumidor.context['metricas'][1]['valor'], '15,0')
        self.assertEqual(ong.context['metricas'][1]['valor'], '15,0')
        self.assertContains(consumidor, 'Você resgatou 15,0 kg de Kit A em doador@x.com.')
        self.assertNotContains(consumidor, 'Kit B')

    def test_acima_de_mil_kg_mostra_toneladas(self):
        lote = self._retirar('Carga grande', self.ong)
        Lote.objects.filter(pk=lote.pk).update(peso_kg=Decimal('1500'))

        resposta = self._painel(self.ong, 'ong')

        self.assertEqual(resposta.context['metricas'][1]['unidade'], 't')
        self.assertEqual(resposta.context['metricas'][1]['valor'], '1,50')

    def test_tendencia_compara_com_o_mes_anterior(self):
        agora = timezone.now()
        self._retirar('Atual', self.consumidor, agora)
        self._retirar('Anterior', self.consumidor, agora - timedelta(days=35))

        resposta = self._painel(self.doador, 'doador')

        self.assertEqual(resposta.context['metricas'][0]['tendencia'], '+0% este mês')

    def test_grafico_tem_seis_meses_e_a_maior_barra_a_100(self):
        self._retirar('Atual', self.consumidor)

        resposta = self._painel(self.doador, 'doador')

        grafico = resposta.context['grafico']
        self.assertEqual(len(grafico), 6)
        self.assertEqual([b['altura'] for b in grafico], [0, 0, 0, 0, 0, 100])
        self.assertContains(resposta, 'height: 100%')

    def test_link_do_relatorio_completo(self):
        resposta = self._painel(self.doador, 'doador')

        self.assertContains(resposta, f'href="{reverse("metricas:relatorio", args=["doador"])}"')

    def test_relatorio_lista_retiradas_e_totais_por_mes(self):
        self._retirar('Kit A', self.consumidor)
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.doador)

        resposta = self.client.get(reverse('metricas:relatorio', args=['doador']))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['total'], {'kg': '15,0', 'co2': '12,3', 'refeicoes': '38', 'retiradas': 1})
        self.assertEqual(len(resposta.context['meses']), 12)
        self.assertContains(resposta, 'Kit A')
        self.assertContains(resposta, 'Retirado por')

    def test_relatorio_de_outro_perfil_redireciona(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.consumidor)

        resposta = self.client.get(reverse('metricas:relatorio', args=['doador']))

        self.assertRedirects(resposta, reverse('metricas:dashboard_consumidor'))

    def test_perfil_inexistente_na_url_nao_quebra(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.consumidor)

        resposta = self.client.get(reverse('metricas:relatorio', args=['admin']))

        self.assertEqual(resposta.status_code, 404)
