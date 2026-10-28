from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

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
