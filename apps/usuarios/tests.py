from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import Client, TestCase
from django.urls import reverse

from apps.auth.cookies import ACCESS_COOKIE
from apps.auth.tokens import emitir_access

from .perfis import PERFIS, url_painel_do_usuario


class SelecaoPerfilTests(TestCase):
    def test_index_lista_os_tres_perfis(self):
        resposta = self.client.get(reverse('usuarios:index'))

        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'usuarios/index.html')
        for perfil in ('doador', 'consumidor', 'ong'):
            self.assertContains(resposta, f'href="{reverse(f"jwt_auth:login_{perfil}")}"')


class PerfisTests(TestCase):
    def test_perfis_iguais_aos_tipos_de_usuario(self):
        Usuario = get_user_model()
        tipos = {valor for valor, _ in Usuario.TipoPerfil.choices} - {Usuario.TipoPerfil.ADMIN}

        self.assertEqual(set(PERFIS), tipos)

    def test_painel_do_usuario(self):
        Usuario = get_user_model()
        doador = Usuario(tipo_perfil='doador')
        admin = Usuario(tipo_perfil='admin')

        self.assertEqual(url_painel_do_usuario(doador), '/dashboard/doador/')
        self.assertEqual(url_painel_do_usuario(admin), reverse('admin:index'))

    def test_iniciais(self):
        self.assertEqual(get_user_model()(nome='instituto esperança social').iniciais, 'IE')


class EstaticosCompartilhadosTests(TestCase):
    def test_folha_de_estilo_global_e_encontrada(self):
        self.assertIsNotNone(finders.find('css/style.css'))

    def test_script_do_menu_mobile_e_encontrado(self):
        self.assertIsNotNone(finders.find('js/menu.js'))


class PaginasDeErroTests(TestCase):
    def test_404_em_portugues_com_a_identidade_do_site(self):
        resposta = self.client.get('/nao-existe/')

        self.assertContains(resposta, 'Página não encontrada', status_code=404)
        self.assertContains(resposta, 'Prato Cheio', status_code=404)

    def test_falha_de_csrf_usa_a_pagina_propria(self):
        cliente = Client(enforce_csrf_checks=True)

        resposta = cliente.post(reverse('jwt_auth:login_ong'), {'email': 'a@b.com', 'senha': 'x'})

        self.assertContains(resposta, 'Não foi possível confirmar o envio', status_code=403)

    def test_500_nao_depende_de_contexto(self):
        html = render_to_string('500.html')

        self.assertIn('Algo deu errado do nosso lado', html)
        self.assertIn('Prato Cheio', html)


class MarcacaoDasPaginasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ong = get_user_model().objects.create_user(
            email='ong@exemplo.com', password='x', nome='ONG', tipo_perfil='ong', status_conta='aprovado',
        )

    def _logado(self, rota):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.ong)
        return self.client.get(reverse(rota))

    def test_area_logada_tem_noindex_link_para_pular_e_aria_current(self):
        resposta = self._logado('lotes:explorar')

        self.assertContains(resposta, '<meta name="robots" content="noindex, nofollow">', html=True)
        self.assertContains(resposta, 'href="#conteudo"')
        self.assertContains(resposta, 'id="conteudo"')
        self.assertContains(resposta, 'aria-current="page"', count=1)

    def test_pagina_de_acesso_tem_link_para_pular_e_nao_tem_noindex(self):
        resposta = self.client.get(reverse('jwt_auth:login_ong'))

        self.assertContains(resposta, 'href="#conteudo"')
        self.assertContains(resposta, 'id="conteudo"')
        self.assertNotContains(resposta, 'noindex')
        self.assertContains(resposta, 'autocomplete="current-password"')

    def test_canonical_nao_leva_a_query_string(self):
        resposta = self.client.get(reverse('jwt_auth:login_ong') + '?x=1')

        self.assertContains(resposta, '<link rel="canonical" href="http://testserver/login/ong/">', html=True)

    def test_robots_txt_na_raiz_bloqueia_admin_auth_e_areas_logadas(self):
        resposta = self.client.get('/robots.txt')

        self.assertEqual(resposta.status_code, 200)
        conteudo = resposta.content.decode() if hasattr(resposta, 'content') else b''.join(resposta.streaming_content).decode()
        for caminho in ('/admin/', '/auth/', '/dashboard/', '/meus-lotes/'):
            self.assertIn(f'Disallow: {caminho}', conteudo)
