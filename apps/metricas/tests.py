from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.auth.cookies import ACCESS_COOKIE
from apps.auth.tokens import emitir_access


class PainelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.usuarios = {
            perfil: Usuario.objects.create_user(
                email=f'{perfil}@exemplo.com', password='x', nome=nome, tipo_perfil=perfil,
                status_conta=Usuario.StatusConta.APROVADO,
            )
            for perfil, nome in (('doador', 'Supermercado Central'), ('consumidor', 'João Silva'), ('ong', 'Instituto Esperança'))
        }

    def _logar(self, perfil):
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.usuarios[perfil])

    def test_rotas(self):
        self.assertEqual(reverse('metricas:dashboard_doador'), '/dashboard/doador/')
        self.assertEqual(reverse('metricas:dashboard_consumidor'), '/dashboard/consumidor/')
        self.assertEqual(reverse('metricas:dashboard_ong'), '/dashboard/ong/')

    def test_painel_exibe_usuario_logado_e_metricas_do_perfil(self):
        casos = {
            'doador': ('Painel do Doador', 'Supermercado Central', 'SC', 'Últimas Retiradas'),
            'consumidor': ('Painel do Consumidor', 'João Silva', 'JS', 'Seus Resgates'),
            'ong': ('Painel da ONG', 'Instituto Esperança', 'IE', 'Seus Resgates'),
        }
        for perfil, (titulo, nome, iniciais, atividades) in casos.items():
            with self.subTest(perfil=perfil):
                self._logar(perfil)

                resposta = self.client.get(reverse(f'metricas:dashboard_{perfil}'))

                self.assertEqual(resposta.status_code, 200)
                self.assertContains(resposta, f'<title>{titulo} | Prato Cheio</title>', html=True)
                self.assertContains(resposta, f'<div class="profile-name">{nome}</div>', html=True)
                self.assertContains(resposta, f'<div class="avatar">{iniciais}</div>', html=True)
                self.assertContains(resposta, f'<h2>{atividades}</h2>', html=True)
                self.assertContains(resposta, f'action="{reverse("jwt_auth:sair")}"')

    def test_painel_de_outro_perfil_redireciona_para_o_proprio(self):
        self._logar('consumidor')

        resposta = self.client.get(reverse('metricas:dashboard_doador'))

        self.assertRedirects(resposta, reverse('metricas:dashboard_consumidor'))

    def test_menu_do_doador_e_dos_receptores(self):
        self._logar('doador')
        doador = self.client.get(reverse('metricas:dashboard_doador'))
        self._logar('ong')
        ong = self.client.get(reverse('metricas:dashboard_ong'))

        self.assertContains(doador, 'Meus Lotes')
        self.assertNotContains(doador, 'Explorar Lotes')
        self.assertContains(ong, 'Explorar Lotes')
        self.assertNotContains(ong, 'Meus Lotes')
