import shutil
import tempfile
from datetime import timedelta
from io import BytesIO, StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.auth.cookies import ACCESS_COOKIE
from apps.auth.tokens import emitir_access

from . import services
from .models import Alimento, Categoria, Lote, Reserva
from .selectors import lotes_na_vitrine
from .tests import CENTRO, _criar_estabelecimento, _criar_lote


def _usuario(email, perfil):
    return get_user_model().objects.create_user(
        email=email, password='x', nome=email.split('@')[0].title(), tipo_perfil=perfil, status_conta='aprovado',
    )


class FluxoDeReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.estabelecimento = _criar_estabelecimento('doador@x.com', CENTRO, '11222333000181')
        cls.doador = cls.estabelecimento.usuario
        cls.consumidor = _usuario('joao@x.com', 'consumidor')
        cls.ong = _usuario('ong@x.com', 'ong')

    def setUp(self):
        self.lote = _criar_lote(self.estabelecimento, 'Kit hortifruti', dias=1)

    def _logar(self, usuario):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(usuario)

    def test_reservar_marca_lote_e_cria_reserva_valida_ate_o_fim_da_retirada(self):
        self._logar(self.consumidor)

        resposta = self.client.post(reverse('lotes:reservar', args=[self.lote.pk]), follow=True)

        self.assertRedirects(resposta, reverse('lotes:minhas_reservas'))
        self.assertContains(resposta, 'Lote reservado!')
        self.lote.refresh_from_db()
        reserva = Reserva.objects.get()
        self.assertEqual(self.lote.status, Lote.Status.RESERVADO)
        self.assertEqual((reserva.usuario, reserva.status), (self.consumidor, Reserva.Status.ATIVA))
        self.assertEqual(reserva.data_expiracao, self.lote.retirada_fim)
        self.assertNotIn(self.lote, lotes_na_vitrine())

    def test_so_um_receptor_reserva_o_lote(self):
        self._logar(self.consumidor)
        self.client.post(reverse('lotes:reservar', args=[self.lote.pk]))
        self._logar(self.ong)

        resposta = self.client.post(reverse('lotes:reservar', args=[self.lote.pk]), follow=True)

        self.assertContains(resposta, 'não está mais disponível')
        self.assertEqual(Reserva.objects.count(), 1)

    def test_reservar_exige_post_e_perfil_receptor(self):
        self._logar(self.consumidor)
        self.assertEqual(self.client.get(reverse('lotes:reservar', args=[self.lote.pk])).status_code, 405)

        self._logar(self.doador)
        resposta = self.client.post(reverse('lotes:reservar', args=[self.lote.pk]))

        self.assertRedirects(resposta, reverse('metricas:dashboard_doador'))
        self.assertFalse(Reserva.objects.exists())

    def test_nao_reserva_lote_com_janela_encerrada_ou_inexistente(self):
        self.lote.retirada_inicio = timezone.now() - timedelta(hours=3)
        self.lote.retirada_fim = timezone.now() - timedelta(hours=1)
        self.lote.save()

        with self.assertRaisesMessage(services.RegraDeNegocio, 'janela de retirada'):
            services.reservar_lote(self.consumidor, self.lote.pk)
        with self.assertRaisesMessage(services.RegraDeNegocio, 'não encontrado'):
            services.reservar_lote(self.consumidor, 999999)

    def test_cancelar_devolve_o_lote_a_vitrine(self):
        reserva = services.reservar_lote(self.consumidor, self.lote.pk)
        self._logar(self.consumidor)

        resposta = self.client.post(reverse('lotes:cancelar_reserva', args=[reserva.pk]), follow=True)

        self.assertContains(resposta, 'Reserva cancelada')
        reserva.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual((reserva.status, self.lote.status), (Reserva.Status.CANCELADA, Lote.Status.DISPONIVEL))

    def test_nao_cancela_reserva_de_outra_pessoa(self):
        reserva = services.reservar_lote(self.consumidor, self.lote.pk)
        self._logar(self.ong)

        self.client.post(reverse('lotes:cancelar_reserva', args=[reserva.pk]))

        reserva.refresh_from_db()
        self.assertEqual(reserva.status, Reserva.Status.ATIVA)

    def test_minhas_reservas_lista_somente_as_proprias(self):
        services.reservar_lote(self.consumidor, self.lote.pk)
        self._logar(self.ong)

        resposta = self.client.get(reverse('lotes:minhas_reservas'))

        self.assertContains(resposta, 'Você ainda não reservou nenhum lote.')
        self._logar(self.consumidor)
        self.assertContains(self.client.get(reverse('lotes:minhas_reservas')), 'Kit hortifruti')

    def test_reserva_vencida_expira_e_o_lote_volta_a_disponivel(self):
        reserva = services.reservar_lote(self.consumidor, self.lote.pk)
        Reserva.objects.filter(pk=reserva.pk).update(data_expiracao=timezone.now() - timedelta(minutes=1))

        expiradas, _ = services.atualizar_pendencias()

        reserva.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(expiradas, 1)
        self.assertEqual((reserva.status, self.lote.status), (Reserva.Status.EXPIRADA, Lote.Status.DISPONIVEL))

    def test_reserva_vencida_de_lote_fora_da_validade_deixa_o_lote_expirado(self):
        reserva = services.reservar_lote(self.consumidor, self.lote.pk)
        Reserva.objects.filter(pk=reserva.pk).update(data_expiracao=timezone.now() - timedelta(minutes=1))
        Lote.objects.filter(pk=self.lote.pk).update(data_validade=timezone.localdate() - timedelta(days=1))

        services.expirar_reservas()

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, Lote.Status.EXPIRADO)

    def test_vitrine_aplica_expiracao_ao_listar(self):
        reserva = services.reservar_lote(self.consumidor, self.lote.pk)
        Reserva.objects.filter(pk=reserva.pk).update(data_expiracao=timezone.now() - timedelta(minutes=1))
        Lote.objects.filter(pk=self.lote.pk).update(retirada_fim=timezone.now() + timedelta(hours=1))
        self._logar(self.ong)

        resposta = self.client.get(reverse('lotes:explorar'))

        self.assertContains(resposta, 'Kit hortifruti')

    def test_lote_disponivel_vencido_vira_expirado(self):
        vencido = _criar_lote(self.estabelecimento, 'Vencido', dias=-2)

        self.assertEqual(services.expirar_lotes(), 1)

        vencido.refresh_from_db()
        self.assertEqual(vencido.status, Lote.Status.EXPIRADO)

    def test_comando_atualizar_status(self):
        _criar_lote(self.estabelecimento, 'Vencido', dias=-2)
        saida = StringIO()

        call_command('atualizar_status', stdout=saida)

        self.assertIn('1 lote(s) expirado(s)', saida.getvalue())

    def test_doador_confirma_retirada(self):
        services.reservar_lote(self.consumidor, self.lote.pk)
        self._logar(self.doador)

        resposta = self.client.post(reverse('lotes:registrar_retirada', args=[self.lote.pk]), {'resultado': 'retirado'}, follow=True)

        self.assertContains(resposta, 'Retirada confirmada')
        self.lote.refresh_from_db()
        reserva = Reserva.objects.get()
        self.assertEqual((self.lote.status, reserva.status), (Lote.Status.RETIRADO, Reserva.Status.CONFIRMADA))
        self.assertIsNotNone(reserva.data_confirmacao)

    def test_doador_registra_nao_retirada(self):
        services.reservar_lote(self.consumidor, self.lote.pk)
        self._logar(self.doador)

        self.client.post(reverse('lotes:registrar_retirada', args=[self.lote.pk]), {'resultado': 'nao_retirado'})

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, Lote.Status.NAO_RETIRADO)
        self.assertEqual(Reserva.objects.get().status, Reserva.Status.NAO_RETIRADA)

    def test_outro_doador_nao_confirma_retirada(self):
        services.reservar_lote(self.consumidor, self.lote.pk)
        intruso = _criar_estabelecimento('intruso@x.com', CENTRO, '22333444000172').usuario
        self._logar(intruso)

        resposta = self.client.post(reverse('lotes:registrar_retirada', args=[self.lote.pk]), {'resultado': 'retirado'}, follow=True)

        self.assertContains(resposta, 'não tem reserva ativa')
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, Lote.Status.RESERVADO)

    def test_meus_lotes_mostra_quem_reservou_e_os_botoes(self):
        services.reservar_lote(self.consumidor, self.lote.pk)
        self._logar(self.doador)

        resposta = self.client.get(reverse('lotes:meus_lotes'))

        self.assertContains(resposta, 'Reservado por Joao')
        self.assertContains(resposta, 'Confirmar retirada')

    def test_exclui_lote_disponivel_mas_nao_reservado(self):
        reservado = _criar_lote(self.estabelecimento, 'Reservado', status=Lote.Status.RESERVADO)
        self._logar(self.doador)

        self.client.post(reverse('lotes:excluir_lote', args=[self.lote.pk]))
        resposta = self.client.post(reverse('lotes:excluir_lote', args=[reservado.pk]), follow=True)

        self.assertFalse(Lote.objects.filter(pk=self.lote.pk).exists())
        self.assertTrue(Lote.objects.filter(pk=reservado.pk).exists())
        self.assertContains(resposta, 'não podem ser excluídos')

    def test_nao_exclui_lote_de_outro_doador_nem_por_get(self):
        outro = _criar_estabelecimento('outro@x.com', CENTRO, '22333444000172').usuario
        self._logar(outro)

        self.client.post(reverse('lotes:excluir_lote', args=[self.lote.pk]))

        self.assertTrue(Lote.objects.filter(pk=self.lote.pk).exists())
        self.assertEqual(self.client.get(reverse('lotes:excluir_lote', args=[self.lote.pk])).status_code, 405)


class FiltrosDaVitrineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        centro = _criar_estabelecimento('centro@x.com', CENTRO, '11222333000181')
        padaria = _criar_estabelecimento('padaria@x.com', CENTRO, '22333444000172')
        padaria.bairro = 'Cambuí'
        padaria.save()
        _criar_lote(centro, 'Tomates frescos')
        pao = Alimento.objects.filter(categoria__nome='Padaria').first()
        Lote.objects.create(
            estabelecimento=padaria, categoria=pao.categoria, alimento=pao, descricao='Pão francês',
            quantidade=5, unidade='kg', peso_kg=5, data_validade=timezone.localdate(),
            retirada_inicio=timezone.now(), retirada_fim=timezone.now() + timedelta(hours=2),
        )
        cls.consumidor = _usuario('joao@x.com', 'consumidor')

    def _descricoes(self, **filtros):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.consumidor)
        resposta = self.client.get(reverse('lotes:explorar'), filtros)
        self.assertEqual(resposta.status_code, 200)
        return sorted(lote.descricao for lote in resposta.context['lotes'])

    def test_busca_ignora_acentos_e_maiusculas(self):
        self.assertEqual(self._descricoes(q='PAO'), ['Pão francês'])
        self.assertEqual(self._descricoes(q='tomate'), ['Tomates frescos'])
        self.assertEqual(self._descricoes(q='inexistente'), [])

    def test_busca_pelo_estabelecimento(self):
        self.assertEqual(self._descricoes(q='padaria@x.com'), ['Pão francês'])

    def test_filtro_por_categoria_e_bairro(self):
        padaria = Categoria.objects.get(nome='Padaria')

        self.assertEqual(self._descricoes(categoria=padaria.pk), ['Pão francês'])
        self.assertEqual(self._descricoes(bairro='Cambuí'), ['Pão francês'])
        self.assertEqual(self._descricoes(bairro='Centro'), ['Tomates frescos'])
        self.assertEqual(self._descricoes(categoria='abc'), ['Pão francês', 'Tomates frescos'])

    def test_selects_so_oferecem_opcoes_com_lotes(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.consumidor)

        resposta = self.client.get(reverse('lotes:explorar'))

        self.assertEqual(resposta.context['bairros'], ['Cambuí', 'Centro'])
        self.assertEqual({c.nome for c in resposta.context['categorias']}, {'Hortifruti', 'Padaria'})

    def test_lote_com_janela_de_retirada_encerrada_nao_aparece(self):
        estab = _criar_estabelecimento('encerrado@x.com', CENTRO, '33444555000163')
        lote = _criar_lote(estab, 'Janela encerrada')
        lote.retirada_inicio = timezone.now() - timedelta(hours=4)
        lote.retirada_fim = timezone.now() - timedelta(hours=1)
        lote.save()

        self.assertNotIn('Janela encerrada', self._descricoes())


class FotoDoLoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.estabelecimento = _criar_estabelecimento('doador@x.com', CENTRO, '11222333000181')
        cls.tomate = Alimento.objects.get(cod_pof=6705101, cod_preparo=99)

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        configuracao = override_settings(MEDIA_ROOT=self.media)
        configuracao.enable()
        self.addCleanup(configuracao.disable)
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.estabelecimento.usuario)

    def _imagem(self, nome='tomate.png', formato='PNG', tipo='image/png'):
        buffer = BytesIO()
        Image.new('RGB', (20, 20), 'red').save(buffer, formato)
        return SimpleUploadedFile(nome, buffer.getvalue(), content_type=tipo)

    def _dados(self, **alteracoes):
        amanha = timezone.localdate() + timedelta(days=1)
        dados = {
            'alimento': self.tomate.pk, 'categoria': '', 'descricao': 'Tomates com foto', 'quantidade': '5',
            'unidade': 'kg', 'peso_kg': '', 'data_validade': amanha.isoformat(),
            'retirada_inicio': f'{amanha.isoformat()}T09:00', 'retirada_fim': f'{amanha.isoformat()}T11:00',
        }
        dados.update(alteracoes)
        return dados

    def test_upload_grava_arquivo_e_vitrine_usa_a_foto(self):
        resposta = self.client.post(reverse('lotes:novo_lote'), self._dados(foto=self._imagem()))

        self.assertRedirects(resposta, reverse('lotes:meus_lotes'))
        lote = Lote.objects.get()
        self.assertTrue(lote.foto.name.startswith('lotes/'))
        self.assertEqual(lote.imagem_enviada, lote.foto.url)
        consumidor = _usuario('joao@x.com', 'consumidor')
        self.client.cookies[ACCESS_COOKIE] = emitir_access(consumidor)
        self.assertContains(self.client.get(reverse('lotes:explorar')), f'src="{lote.foto.url}"')

    def test_arquivo_enviado_e_servido_em_media(self):
        self.client.post(reverse('lotes:novo_lote'), self._dados(foto=self._imagem()))

        resposta = self.client.get(Lote.objects.get().foto.url)

        self.assertEqual(resposta.status_code, 200)

    def test_rejeita_arquivo_que_nao_e_imagem(self):
        falso = SimpleUploadedFile('malicioso.png', b'nao sou imagem', content_type='image/png')

        resposta = self.client.post(reverse('lotes:novo_lote'), self._dados(foto=falso))

        self.assertIn('foto', resposta.context['form'].errors)
        self.assertFalse(Lote.objects.exists())

    def test_rejeita_foto_acima_do_limite(self):
        with override_settings(FOTO_LOTE_MAX_MB=0):
            resposta = self.client.post(reverse('lotes:novo_lote'), self._dados(foto=self._imagem()))

        self.assertContains(resposta, 'no máximo 0 MB')

    def test_rejeita_formato_nao_permitido(self):
        gif = self._imagem('a.gif', 'GIF', 'image/gif')

        resposta = self.client.post(reverse('lotes:novo_lote'), self._dados(foto=gif))

        self.assertContains(resposta, 'JPG, PNG ou WebP')

    def test_excluir_lote_apaga_a_foto(self):
        self.client.post(reverse('lotes:novo_lote'), self._dados(foto=self._imagem()))
        lote = Lote.objects.get()
        caminho = lote.foto.path

        self.client.post(reverse('lotes:excluir_lote', args=[lote.pk]))

        import os
        self.assertFalse(os.path.exists(caminho))


class ReclassificarAlimentosTests(TestCase):
    def test_corrige_alimento_fora_da_categoria_e_atualiza_lotes(self):
        arroz = Alimento.objects.get(cod_pof=6300201, cod_preparo=99)
        correta = arroz.categoria
        errada = Categoria.objects.get(nome='Doces')
        Alimento.objects.filter(pk=arroz.pk).update(categoria=errada)
        lote = _criar_lote(_criar_estabelecimento('d@x.com', CENTRO, '11222333000181'), 'Arroz')
        Lote.objects.filter(pk=lote.pk).update(alimento=arroz, categoria=errada)

        saida = StringIO()
        call_command('reclassificar_alimentos', '--simular', stdout=saida)
        arroz.refresh_from_db()
        self.assertEqual(arroz.categoria, errada)
        self.assertIn('seriam reclassificados', saida.getvalue())

        call_command('reclassificar_alimentos', stdout=StringIO())
        arroz.refresh_from_db()
        lote.refresh_from_db()
        self.assertEqual((arroz.categoria, lote.categoria), (correta, correta))

    def test_sem_mudancas_nao_altera_nada(self):
        saida = StringIO()

        call_command('reclassificar_alimentos', stdout=saida)

        self.assertIn('0 alimento(s) reclassificados', saida.getvalue())
