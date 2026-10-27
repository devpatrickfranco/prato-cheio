from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Usuario
from usuarios.tests import criar_doador, criar_usuario

from . import services
from .forms import LoteForm
from .models import Categoria, Lote, Reserva
from .services import RegraDeNegocio


def criar_lote(doador, tipo=Lote.Tipo.DOACAO, preco=None, peso='10', categoria='Hortifruti',
               dias_validade=1, status=Lote.Status.DISPONIVEL):
    agora = timezone.now()
    return Lote.objects.create(
        estabelecimento=doador.estabelecimento,
        categoria=Categoria.objects.get(nome=categoria),
        descricao='Tomates', tipo=tipo, preco=preco,
        quantidade=Decimal(peso), unidade=Lote.Unidade.KG, peso_kg=Decimal(peso),
        data_validade=timezone.localdate() + timedelta(days=dias_validade),
        retirada_inicio=agora + timedelta(hours=1),
        retirada_fim=agora + timedelta(hours=5),
        status=status,
    )


class CategoriasIniciaisTests(TestCase):
    def test_migracao_cria_as_categorias(self):
        self.assertEqual(Categoria.objects.count(), 5)
        self.assertTrue(Categoria.objects.filter(nome='Hortifruti', fator_co2_kg=Decimal('2.50')).exists())


class ReservaTests(TestCase):
    def setUp(self):
        self.doador = criar_doador()
        self.ong = criar_usuario('ong@exemplo.com', Usuario.Perfil.ONG, nome='ONG')
        self.consumidor = criar_usuario('pf@exemplo.com', nome='Consumidor')

    def test_ong_reserva_doacao(self):
        lote = criar_lote(self.doador)
        reserva = services.reservar(lote.pk, self.ong)
        lote.refresh_from_db()
        self.assertEqual(lote.status, Lote.Status.RESERVADO)
        self.assertEqual(reserva.status, Reserva.Status.ATIVA)
        self.assertEqual(reserva.comissao, Decimal('0'))

    def test_consumidor_nao_reserva_doacao(self):
        lote = criar_lote(self.doador)
        with self.assertRaises(RegraDeNegocio):
            services.reservar(lote.pk, self.consumidor)

    def test_ong_nao_compra_lote_a_venda(self):
        lote = criar_lote(self.doador, Lote.Tipo.VENDA, Decimal('40'))
        with self.assertRaises(RegraDeNegocio):
            services.reservar(lote.pk, self.ong)

    def test_venda_calcula_comissao(self):
        lote = criar_lote(self.doador, Lote.Tipo.VENDA, Decimal('40.00'))
        reserva = services.reservar(lote.pk, self.consumidor)
        self.assertEqual(reserva.valor, Decimal('40.00'))
        self.assertEqual(reserva.comissao, Decimal('3.20'))  # 8% de comissao padrao

    def test_doador_nao_reserva_o_proprio_lote(self):
        lote = criar_lote(self.doador, Lote.Tipo.VENDA, Decimal('10'))
        with self.assertRaises(RegraDeNegocio):
            services.reservar(lote.pk, self.doador)

    def test_segundo_usuario_nao_reserva_lote_ja_reservado(self):
        lote = criar_lote(self.doador, Lote.Tipo.VENDA, Decimal('10'))
        services.reservar(lote.pk, self.consumidor)
        outro = criar_usuario('outro@exemplo.com', nome='Outro')
        with self.assertRaises(RegraDeNegocio):
            services.reservar(lote.pk, outro)

    def test_banco_impede_duas_reservas_ativas_do_mesmo_lote(self):
        from django.db import IntegrityError, transaction
        lote = criar_lote(self.doador)
        agora = timezone.now()
        Reserva.objects.create(lote=lote, usuario=self.ong, data_expiracao=agora)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reserva.objects.create(lote=lote, usuario=self.consumidor, data_expiracao=agora)

    def test_lote_vencido_nao_pode_ser_reservado(self):
        lote = criar_lote(self.doador)
        Lote.objects.filter(pk=lote.pk).update(data_validade=timezone.localdate() - timedelta(days=1))
        with self.assertRaises(RegraDeNegocio):
            services.reservar(lote.pk, self.ong)

    def test_cancelar_devolve_lote_para_a_vitrine(self):
        lote = criar_lote(self.doador)
        reserva = services.reservar(lote.pk, self.ong)
        services.cancelar_reserva(reserva.pk, self.ong)
        lote.refresh_from_db()
        self.assertEqual(lote.status, Lote.Status.DISPONIVEL)

    def test_so_o_dono_cancela_a_reserva(self):
        lote = criar_lote(self.doador)
        reserva = services.reservar(lote.pk, self.ong)
        with self.assertRaises(RegraDeNegocio):
            services.cancelar_reserva(reserva.pk, self.consumidor)

    def test_confirmar_retirada_conclui_o_lote(self):
        lote = criar_lote(self.doador)
        reserva = services.reservar(lote.pk, self.ong)
        services.confirmar_retirada(reserva.pk, self.doador)
        lote.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(lote.status, Lote.Status.RETIRADO)
        self.assertEqual(reserva.status, Reserva.Status.CONFIRMADA)
        self.assertIsNotNone(reserva.data_confirmacao)

    def test_outro_doador_nao_confirma_retirada(self):
        lote = criar_lote(self.doador)
        reserva = services.reservar(lote.pk, self.ong)
        intruso = criar_doador('intruso@exemplo.com', 'Intruso', cnpj='22333444000172')
        with self.assertRaises(RegraDeNegocio):
            services.confirmar_retirada(reserva.pk, intruso)

    def test_reserva_nao_retirada_expira_com_o_prazo(self):
        lote = criar_lote(self.doador)
        reserva = services.reservar(lote.pk, self.ong)
        services.expirar_pendencias(timezone.now() + timedelta(days=1))
        lote.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, Reserva.Status.EXPIRADA)
        self.assertEqual(lote.status, Lote.Status.NAO_RETIRADO)

    def test_lote_disponivel_vencido_vira_expirado(self):
        lote = criar_lote(self.doador)
        services.expirar_pendencias(timezone.now() + timedelta(days=3))
        lote.refresh_from_db()
        self.assertEqual(lote.status, Lote.Status.EXPIRADO)

    def test_so_remove_lote_disponivel(self):
        lote = criar_lote(self.doador)
        services.reservar(lote.pk, self.ong)
        with self.assertRaises(RegraDeNegocio):
            services.remover_lote(lote.pk, self.doador)


class VitrineTests(TestCase):
    def setUp(self):
        self.doador = criar_doador()
        self.ong = criar_usuario('ong@exemplo.com', Usuario.Perfil.ONG, nome='ONG')
        self.consumidor = criar_usuario('pf@exemplo.com', nome='Consumidor')
        self.doacao = criar_lote(self.doador)
        self.venda = criar_lote(self.doador, Lote.Tipo.VENDA, Decimal('30'))

    def test_ong_ve_so_doacoes(self):
        self.assertEqual(list(services.lotes_da_vitrine(self.ong)), [self.doacao])

    def test_consumidor_ve_so_vendas(self):
        self.assertEqual(list(services.lotes_da_vitrine(self.consumidor)), [self.venda])

    def test_doador_nao_ve_os_proprios_lotes(self):
        self.assertEqual(list(services.lotes_da_vitrine(self.doador)), [])

    def test_lote_reservado_sai_da_vitrine(self):
        services.reservar(self.venda.pk, self.consumidor)
        self.assertEqual(list(services.lotes_da_vitrine(self.consumidor)), [])


class ViewsTests(TestCase):
    def setUp(self):
        self.doador = criar_doador()
        self.consumidor = criar_usuario('pf@exemplo.com', nome='Consumidor')
        self.venda = criar_lote(self.doador, Lote.Tipo.VENDA, Decimal('30'))

    def entrar(self, email, rota):
        self.client.post(reverse(rota), {'email': email, 'senha': 'senha-forte-123'})

    def test_consumidor_reserva_pela_vitrine(self):
        self.entrar('pf@exemplo.com', 'usuarios:login_pf')
        pagina = self.client.get(reverse('produtos:explorar'))
        self.assertContains(pagina, 'Comprar e reservar')
        resposta = self.client.post(reverse('produtos:reservar_lote', args=[self.venda.pk]))
        self.assertRedirects(resposta, reverse('produtos:minhas_reservas'))
        self.assertTrue(Reserva.objects.filter(lote=self.venda, usuario=self.consumidor).exists())

    def test_reservar_exige_post(self):
        self.entrar('pf@exemplo.com', 'usuarios:login_pf')
        resposta = self.client.get(reverse('produtos:reservar_lote', args=[self.venda.pk]))
        self.assertEqual(resposta.status_code, 405)

    def test_filtro_por_bairro(self):
        self.entrar('pf@exemplo.com', 'usuarios:login_pf')
        self.assertContains(self.client.get(reverse('produtos:explorar'), {'bairro': 'Centro'}), 'Tomates')
        self.assertNotContains(self.client.get(reverse('produtos:explorar'), {'bairro': 'Outro'}), 'Tomates')

    def test_doador_publica_lote_com_fotos(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        from PIL import Image

        def imagem(nome):
            buffer = io.BytesIO()
            Image.new('RGB', (4, 4), 'green').save(buffer, 'PNG')
            return SimpleUploadedFile(nome, buffer.getvalue(), content_type='image/png')

        self.entrar('doador@exemplo.com', 'usuarios:login_pj')
        agora = timezone.localtime() + timedelta(hours=1)
        resposta = self.client.post(reverse('produtos:lote_novo'), {
            'descricao': 'Pães do dia', 'categoria': Categoria.objects.get(nome='Padaria').pk,
            'tipo': 'doacao', 'quantidade': '5', 'unidade': 'kg',
            'data_validade': (timezone.localdate() + timedelta(days=1)).isoformat(),
            'retirada_inicio': agora.strftime('%Y-%m-%dT%H:%M'),
            'retirada_fim': (agora + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M'),
            'foto': imagem('foto.png'), 'foto_validade': imagem('validade.png'),
        })
        self.assertRedirects(resposta, reverse('produtos:meus_lotes'))
        lote = Lote.objects.get(descricao='Pães do dia')
        self.assertEqual(lote.peso_kg, Decimal('5'))  # derivado da quantidade em kg
        self.assertIsNone(lote.preco)
        lote.foto.delete(save=False)
        lote.foto_validade.delete(save=False)


class LoteFormTests(TestCase):
    def dados(self, **extra):
        agora = timezone.localtime() + timedelta(hours=1)
        base = {
            'descricao': 'Tomates', 'categoria': Categoria.objects.first().pk, 'tipo': 'doacao',
            'quantidade': '5', 'unidade': 'kg',
            'data_validade': (timezone.localdate() + timedelta(days=1)).isoformat(),
            'retirada_inicio': agora.strftime('%Y-%m-%dT%H:%M'),
            'retirada_fim': (agora + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
        }
        base.update(extra)
        return base

    def form(self, **extra):
        form = LoteForm(self.dados(**extra))
        form.fields['foto_validade'].required = False  # foco nas demais regras
        return form

    def test_venda_exige_preco(self):
        form = self.form(tipo='venda')
        self.assertFalse(form.is_valid())
        self.assertIn('preco', form.errors)

    def test_validade_no_passado_e_recusada(self):
        form = self.form(data_validade=(timezone.localdate() - timedelta(days=1)).isoformat())
        self.assertFalse(form.is_valid())
        self.assertIn('data_validade', form.errors)

    def test_fim_antes_do_inicio_e_recusado(self):
        agora = timezone.localtime() + timedelta(hours=3)
        form = self.form(
            retirada_inicio=agora.strftime('%Y-%m-%dT%H:%M'),
            retirada_fim=(agora - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
        )
        self.assertFalse(form.is_valid())
        self.assertIn('retirada_fim', form.errors)

    def test_unidade_exige_peso_estimado(self):
        form = self.form(unidade='un')
        self.assertFalse(form.is_valid())
        self.assertIn('peso_kg', form.errors)

    def test_doacao_descarta_preco(self):
        form = self.form(preco='20')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['preco'])
