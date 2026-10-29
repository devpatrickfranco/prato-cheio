import re
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import limitador
from .cookies import ACCESS_COOKIE, REFRESH_COOKIE
from .models import TentativaLogin, TokenRevogado
from .tokens import ACCESS, TokenInvalido, decodificar, emitir_tokens, revogar

SENHA = 'senha-forte-123'


class BaseSegurancaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.usuario = Usuario.objects.create_user(
            email='ong@exemplo.com', password=SENHA, nome='ONG Exemplo',
            tipo_perfil='ong', status_conta='aprovado',
        )


class RevogacaoDeTokenTests(BaseSegurancaTests):
    def test_token_revogado_deixa_de_valer(self):
        access = emitir_tokens(self.usuario)['access']
        self.assertEqual(decodificar(access, ACCESS)['sub'], str(self.usuario.pk))

        self.assertTrue(revogar(access))

        with self.assertRaisesMessage(TokenInvalido, 'revogado'):
            decodificar(access, ACCESS)

    def test_revogar_e_idempotente_e_ignora_lixo(self):
        access = emitir_tokens(self.usuario)['access']

        self.assertTrue(revogar(access))
        self.assertTrue(revogar(access))
        self.assertFalse(revogar('nao-e-um-token'))
        self.assertFalse(revogar(''))
        self.assertEqual(TokenRevogado.objects.count(), 1)

    def test_logout_revoga_os_tokens_dos_cookies(self):
        self.client.post(reverse('jwt_auth:login_ong'), {'email': 'ong@exemplo.com', 'senha': SENHA})
        access = self.client.cookies[ACCESS_COOKIE].value
        refresh = self.client.cookies[REFRESH_COOKIE].value

        self.client.post(reverse('jwt_auth:sair'))

        self.assertEqual(TokenRevogado.objects.count(), 2)
        # Mesmo reapresentando os cookies antigos, a sessão não volta.
        self.client.cookies[ACCESS_COOKIE] = access
        self.client.cookies[REFRESH_COOKIE] = refresh
        self.assertRedirects(self.client.get(reverse('metricas:dashboard_ong')), reverse('usuarios:index'))

    def test_api_logout_revoga_refresh_e_access(self):
        tokens = self.client.post(
            reverse('jwt_auth:token'), {'email': 'ong@exemplo.com', 'senha': SENHA}, content_type='application/json',
        ).json()

        resposta = self.client.post(
            reverse('jwt_auth:revogar_token'), {'refresh': tokens['refresh']}, content_type='application/json',
            headers={'Authorization': f'Bearer {tokens["access"]}'},
        )

        self.assertEqual(resposta.status_code, 200)
        renovar = self.client.post(reverse('jwt_auth:renovar_token'), {'refresh': tokens['refresh']}, content_type='application/json')
        eu = self.client.get(reverse('jwt_auth:usuario_atual'), headers={'Authorization': f'Bearer {tokens["access"]}'})
        self.assertEqual((renovar.status_code, eu.status_code), (401, 401))

    def test_api_revogar_sem_token_valido(self):
        resposta = self.client.post(reverse('jwt_auth:revogar_token'), {'refresh': 'x'}, content_type='application/json')

        self.assertEqual(resposta.status_code, 400)

    def test_limpar_auth_remove_so_o_que_expirou(self):
        TokenRevogado.objects.create(jti='a' * 32, expira_em=timezone.now() - timedelta(days=1))
        TokenRevogado.objects.create(jti='b' * 32, expira_em=timezone.now() + timedelta(days=1))
        TentativaLogin.objects.create(email='x@x.com')
        TentativaLogin.objects.filter().update(criado_em=timezone.now() - timedelta(days=1))
        TentativaLogin.objects.create(email='y@x.com')

        call_command('limpar_auth', stdout=StringIO())

        self.assertEqual(list(TokenRevogado.objects.values_list('jti', flat=True)), ['b' * 32])
        self.assertEqual(list(TentativaLogin.objects.values_list('email', flat=True)), ['y@x.com'])


class LimiteDeTentativasTests(BaseSegurancaTests):
    def _errar(self, vezes, email='ong@exemplo.com'):
        for _ in range(vezes):
            resposta = self.client.post(reverse('jwt_auth:login_ong'), {'email': email, 'senha': 'errada'})
        return resposta

    def test_bloqueia_apos_cinco_falhas_mesmo_com_a_senha_certa(self):
        self._errar(limitador.MAX_FALHAS_EMAIL)

        resposta = self.client.post(reverse('jwt_auth:login_ong'), {'email': 'ong@exemplo.com', 'senha': SENHA})

        self.assertEqual(resposta.status_code, 429)
        self.assertContains(resposta, 'Muitas tentativas', status_code=429)
        self.assertNotIn(ACCESS_COOKIE, resposta.cookies)

    def test_abaixo_do_limite_o_login_certo_zera_as_falhas(self):
        self._errar(limitador.MAX_FALHAS_EMAIL - 1)

        resposta = self.client.post(reverse('jwt_auth:login_ong'), {'email': 'ong@exemplo.com', 'senha': SENHA})

        self.assertRedirects(resposta, reverse('metricas:dashboard_ong'))
        self.assertFalse(TentativaLogin.objects.exists())

    def test_email_e_comparado_sem_diferenciar_maiusculas(self):
        self._errar(limitador.MAX_FALHAS_EMAIL, email='ONG@Exemplo.com')

        resposta = self.client.post(reverse('jwt_auth:login_ong'), {'email': 'ong@exemplo.com', 'senha': SENHA})

        self.assertEqual(resposta.status_code, 429)

    def test_falhas_antigas_deixam_de_contar(self):
        self._errar(limitador.MAX_FALHAS_EMAIL)
        TentativaLogin.objects.update(criado_em=timezone.now() - limitador.JANELA - timedelta(minutes=1))

        resposta = self.client.post(reverse('jwt_auth:login_ong'), {'email': 'ong@exemplo.com', 'senha': SENHA})

        self.assertRedirects(resposta, reverse('metricas:dashboard_ong'))

    def test_bloqueio_por_ip(self):
        for indice in range(limitador.MAX_FALHAS_IP):
            self.client.post(reverse('jwt_auth:login_ong'), {'email': f'alvo{indice}@exemplo.com', 'senha': 'errada'})

        resposta = self.client.post(reverse('jwt_auth:login_ong'), {'email': 'ong@exemplo.com', 'senha': SENHA})

        self.assertEqual(resposta.status_code, 429)

    @override_settings(PROXY_IP_HEADER='HTTP_X_FORWARDED_FOR')
    def test_ip_vem_do_cabecalho_do_proxy_quando_configurado(self):
        for indice in range(limitador.MAX_FALHAS_IP):
            self.client.post(
                reverse('jwt_auth:login_ong'), {'email': f'a{indice}@exemplo.com', 'senha': 'errada'},
                headers={'X-Forwarded-For': '203.0.113.9, 10.0.0.1'},
            )

        mesmo = self.client.post(reverse('jwt_auth:login_ong'), {'email': 'ong@exemplo.com', 'senha': SENHA}, headers={'X-Forwarded-For': '203.0.113.9'})
        outro = self.client.post(reverse('jwt_auth:login_ong'), {'email': 'ong@exemplo.com', 'senha': SENHA}, headers={'X-Forwarded-For': '198.51.100.7'})

        self.assertEqual(mesmo.status_code, 429)
        self.assertEqual(outro.status_code, 302)

    def test_api_tambem_e_limitada(self):
        corpo = {'email': 'ong@exemplo.com', 'senha': 'errada'}
        for _ in range(limitador.MAX_FALHAS_EMAIL):
            self.client.post(reverse('jwt_auth:token'), corpo, content_type='application/json')

        resposta = self.client.post(reverse('jwt_auth:token'), {**corpo, 'senha': SENHA}, content_type='application/json')

        self.assertEqual(resposta.status_code, 429)


class RecuperacaoDeSenhaTests(BaseSegurancaTests):
    def _pedir_link(self, email='ong@exemplo.com'):
        resposta = self.client.post(reverse('jwt_auth:senha_esqueci'), {'email': email})
        self.assertRedirects(resposta, reverse('jwt_auth:senha_enviada'))
        return resposta

    def test_pagina_do_pedido(self):
        resposta = self.client.get(reverse('jwt_auth:senha_esqueci'))

        self.assertContains(resposta, 'Recuperar senha')

    def test_envia_email_com_link_e_a_nova_senha_funciona(self):
        self._pedir_link()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Prato Cheio', mail.outbox[0].subject)
        link = re.search(r'https?://\S+/senha/redefinir/\S+/', mail.outbox[0].body).group(0)
        caminho = link.split('testserver', 1)[1]
        pagina = self.client.get(caminho, follow=True)
        self.assertContains(pagina, 'Criar nova senha')

        resposta = self.client.post(pagina.redirect_chain[-1][0], {'new_password1': 'NovaSenha-987', 'new_password2': 'NovaSenha-987'})

        self.assertRedirects(resposta, reverse('jwt_auth:senha_redefinida'))
        login = self.client.post(reverse('jwt_auth:login_ong'), {'email': 'ong@exemplo.com', 'senha': 'NovaSenha-987'})
        self.assertRedirects(login, reverse('metricas:dashboard_ong'))

    def test_email_desconhecido_nao_revela_nada_e_nao_envia(self):
        self._pedir_link('ninguem@exemplo.com')

        self.assertEqual(len(mail.outbox), 0)

    def test_link_adulterado_e_invalido(self):
        resposta = self.client.get(reverse('jwt_auth:senha_redefinir', args=['AA', 'token-invalido']))

        self.assertContains(resposta, 'Link inválido')

    def test_senha_fraca_e_recusada(self):
        self._pedir_link()
        link = re.search(r'/senha/redefinir/\S+/', mail.outbox[0].body).group(0)
        pagina = self.client.get(link, follow=True)

        resposta = self.client.post(pagina.redirect_chain[-1][0], {'new_password1': '123', 'new_password2': '123'})

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'form-erro')


class AdminDeUsuariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.admin = Usuario.objects.create_superuser(email='admin@exemplo.com', password=SENHA, nome='Admin')
        cls.pendente = Usuario.objects.create_user(email='p@exemplo.com', password=SENHA, nome='Pendente', tipo_perfil='ong')

    def setUp(self):
        self.client.force_login(self.admin)

    def test_acoes_aprovar_e_recusar(self):
        url = reverse('admin:usuarios_usuario_changelist')

        self.client.post(url, {'action': 'aprovar_contas', '_selected_action': [self.pendente.pk]})
        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.status_conta, 'aprovado')

        self.client.post(url, {'action': 'recusar_contas', '_selected_action': [self.pendente.pk]})
        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.status_conta, 'recusado')

    def test_formulario_permite_trocar_a_senha(self):
        pagina = self.client.get(reverse('admin:usuarios_usuario_change', args=[self.pendente.pk]))
        self.assertContains(pagina, 'password/')

        resposta = self.client.post(
            reverse('admin:auth_user_password_change', args=[self.pendente.pk]),
            {'password1': 'OutraSenha-456', 'password2': 'OutraSenha-456'},
        )

        self.assertEqual(resposta.status_code, 302)
        self.pendente.refresh_from_db()
        self.assertTrue(self.pendente.check_password('OutraSenha-456'))

    def test_lista_filtra_pendentes(self):
        resposta = self.client.get(reverse('admin:usuarios_usuario_changelist'), {'status_conta': 'pendente'})

        self.assertEqual([u.email for u in resposta.context['cl'].result_list], ['p@exemplo.com'])
