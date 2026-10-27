from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from produtos import services as produtos_services
from produtos.models import Categoria, Lote
from produtos.tests import criar_lote
from usuarios.models import Usuario
from usuarios.tests import SENHA, criar_doador, criar_usuario

from . import services


class ImpactoTests(TestCase):
    def setUp(self):
        self.doador = criar_doador()
        self.ong = criar_usuario('ong@exemplo.com', Usuario.Perfil.ONG, nome='ONG')

    def retirar(self, peso, categoria='Hortifruti'):
        lote = criar_lote(self.doador, peso=peso, categoria=categoria)
        reserva = produtos_services.reservar(lote.pk, self.ong)
        produtos_services.confirmar_retirada(reserva.pk, self.doador)
        return lote

    def test_resumo_usa_o_fator_da_categoria(self):
        self.retirar('20')
        total = services.resumo(services.reservas_confirmadas(self.doador))
        self.assertEqual(total['kg'], Decimal('20'))
        self.assertEqual(total['co2'], Decimal('50'))  # 20 kg x 2,5
        self.assertEqual(total['refeicoes'], 50)  # 20 kg / 0,4 kg
        self.assertEqual(total['lotes'], 1)

    def test_fator_atualizado_reflete_no_calculo(self):
        self.retirar('10')
        Categoria.objects.filter(nome='Hortifruti').update(fator_co2_kg=Decimal('4.00'))
        total = services.resumo(services.reservas_confirmadas(self.doador))
        self.assertEqual(total['co2'], Decimal('40'))

    def test_lote_so_reservado_nao_conta(self):
        lote = criar_lote(self.doador)
        produtos_services.reservar(lote.pk, self.ong)
        total = services.resumo(services.reservas_confirmadas(self.doador))
        self.assertEqual(total['lotes'], 0)
        self.assertEqual(total['co2'], Decimal('0'))

    def test_cada_perfil_ve_so_o_que_lhe_pertence(self):
        self.retirar('8')
        outra_ong = criar_usuario('outra@exemplo.com', Usuario.Perfil.ONG, nome='Outra')
        self.assertEqual(services.resumo(services.reservas_confirmadas(self.ong))['lotes'], 1)
        self.assertEqual(services.resumo(services.reservas_confirmadas(outra_ong))['lotes'], 0)

    def test_serie_mensal_tem_seis_meses_com_o_atual_por_ultimo(self):
        self.retirar('20')
        serie = services.serie_mensal(services.reservas_confirmadas(self.doador))
        self.assertEqual(len(serie), 6)
        self.assertEqual(serie[-1]['mes'], timezone.localdate().replace(day=1))
        self.assertEqual(serie[-1]['kg'], Decimal('20'))
        self.assertEqual(serie[0]['kg'], Decimal('0'))

    def test_por_categoria_agrupa_os_lotes(self):
        self.retirar('10', 'Hortifruti')
        self.retirar('5', 'Padaria')
        nomes = {c['nome']: c['kg'] for c in services.por_categoria(services.reservas_confirmadas(self.doador))}
        self.assertEqual(nomes, {'Hortifruti': Decimal('10'), 'Padaria': Decimal('5')})

    def test_variacao_percentual(self):
        self.assertEqual(services.variacao_percentual(Decimal('150'), Decimal('100')), 50)
        self.assertEqual(services.variacao_percentual(Decimal('50'), Decimal('100')), -50)
        self.assertIsNone(services.variacao_percentual(Decimal('10'), Decimal('0')))

    def test_nivel_do_doador(self):
        self.assertEqual(services.nivel_do_doador(Decimal('0'))['nome'], 'Semente')
        nivel = services.nivel_do_doador(Decimal('60'))
        self.assertEqual((nivel['nome'], nivel['proximo']), ('Broto', 'Árvore'))
        self.assertEqual(nivel['faltam'], Decimal('140'))
        self.assertIsNone(services.nivel_do_doador(Decimal('900'))['proximo'])


class PainelTests(TestCase):
    def setUp(self):
        self.doador = criar_doador()
        self.ong = criar_usuario('ong@exemplo.com', Usuario.Perfil.ONG, nome='ONG')
        lote = criar_lote(self.doador, peso='20')
        reserva = produtos_services.reservar(lote.pk, self.ong)
        produtos_services.confirmar_retirada(reserva.pk, self.doador)

    def entrar(self, email, rota):
        self.client.post(reverse(rota), {'email': email, 'senha': SENHA})

    def test_painel_do_doador_mostra_impacto_e_nivel(self):
        self.entrar('doador@exemplo.com', 'usuarios:login_pj')
        resposta = self.client.get(reverse('metricas:painel'))
        self.assertContains(resposta, '50,0')  # CO2 evitado
        self.assertContains(resposta, 'Painel do Doador')
        self.assertContains(resposta, 'Semente')

    def test_painel_da_ong_usa_texto_de_contribuicao(self):
        self.entrar('ong@exemplo.com', 'usuarios:login_ong')
        resposta = self.client.get(reverse('metricas:painel'))
        self.assertContains(resposta, 'Sua contribuição')
        self.assertContains(resposta, 'Painel da Instituição')

    def test_relatorio_lista_categorias(self):
        self.entrar('ong@exemplo.com', 'usuarios:login_ong')
        resposta = self.client.get(reverse('metricas:relatorio'))
        self.assertContains(resposta, 'Hortifruti')
        self.assertContains(resposta, '<caption>')
