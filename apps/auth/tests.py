from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .cookies import ACCESS_COOKIE, REFRESH_COOKIE
from .tokens import emitir_tokens

SENHA = 'senha-forte-123'


class BaseAuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.usuario = Usuario.objects.create_user(
            email='ong@exemplo.com', password=SENHA, nome='ONG Exemplo',
            tipo_perfil=Usuario.TipoPerfil.ONG, status_conta=Usuario.StatusConta.APROVADO,
        )


class LoginWebTests(BaseAuthTests):
    def _entrar(self, perfil='ong', senha=SENHA):
        return self.client.post(reverse(f'jwt_auth:login_{perfil}'), {'email': 'ong@exemplo.com', 'senha': senha})

    def test_paginas_de_login_dos_tres_perfis(self):
        for perfil, nome in (('doador', 'Doador'), ('consumidor', 'Consumidor'), ('ong', 'ONG')):
            with self.subTest(perfil=perfil):
                resposta = self.client.get(reverse(f'jwt_auth:login_{perfil}'))

                self.assertEqual(resposta.status_code, 200)
                self.assertContains(resposta, f'<h2>Acesso {nome}</h2>', html=True)

    def test_login_valido_grava_cookies_e_vai_ao_painel(self):
        resposta = self._entrar()

        self.assertRedirects(resposta, reverse('metricas:dashboard_ong'))
        self.assertTrue(resposta.cookies[ACCESS_COOKIE]['httponly'])
        self.assertTrue(resposta.cookies[REFRESH_COOKIE].value)

    def test_login_no_perfil_errado_e_recusado(self):
        resposta = self._entrar(perfil='doador')

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Esta conta não é de Doador')
        self.assertNotIn(ACCESS_COOKIE, resposta.cookies)

    def test_senha_errada_mostra_erro(self):
        resposta = self._entrar(senha='errada')

        self.assertContains(resposta, 'E-mail ou senha inválidos.')
        self.assertNotIn(ACCESS_COOKIE, resposta.cookies)

    def test_conta_pendente_nao_entra(self):
        self.usuario.status_conta = self.usuario.StatusConta.PENDENTE
        self.usuario.save()

        self.assertContains(self._entrar(), 'Sua conta ainda não foi aprovada.')

    def test_sair_apaga_cookies(self):
        self._entrar()

        resposta = self.client.post(reverse('jwt_auth:sair'))

        self.assertRedirects(resposta, reverse('usuarios:index'))
        self.assertEqual(resposta.cookies[ACCESS_COOKIE].value, '')


class RotasProtegidasTests(BaseAuthTests):
    def test_sem_login_volta_para_a_selecao_de_perfil(self):
        for rota in ('metricas:dashboard_ong', 'metricas:dashboard_doador', 'lotes:explorar', 'lotes:meus_lotes'):
            with self.subTest(rota=rota):
                self.assertRedirects(self.client.get(reverse(rota)), reverse('usuarios:index'))

    def test_token_adulterado_e_recusado(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_tokens(self.usuario)['access'] + 'x'

        self.assertRedirects(self.client.get(reverse('metricas:dashboard_ong')), reverse('usuarios:index'))

    def test_perfil_errado_vai_para_o_proprio_painel(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_tokens(self.usuario)['access']

        resposta = self.client.get(reverse('lotes:meus_lotes'))

        self.assertRedirects(resposta, reverse('metricas:dashboard_ong'))

    @override_settings(JWT_ACCESS_TTL=timedelta(seconds=-1))
    def test_access_expirado_e_renovado_pelo_refresh(self):
        tokens = emitir_tokens(self.usuario)
        self.client.cookies[ACCESS_COOKIE] = tokens['access']
        self.client.cookies[REFRESH_COOKIE] = tokens['refresh']

        resposta = self.client.get(reverse('metricas:dashboard_ong'))

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(ACCESS_COOKIE, resposta.cookies)

    def test_usuario_desativado_perde_o_acesso(self):
        self.client.cookies[ACCESS_COOKIE] = emitir_tokens(self.usuario)['access']
        self.usuario.is_active = False
        self.usuario.save()

        self.assertRedirects(self.client.get(reverse('metricas:dashboard_ong')), reverse('usuarios:index'))


class ApiJWTTests(BaseAuthTests):
    def _token(self, senha=SENHA):
        return self.client.post(reverse('jwt_auth:token'), {'email': 'ong@exemplo.com', 'senha': senha}, content_type='application/json')

    def test_login_valido_emite_access_e_refresh(self):
        resposta = self._token()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(set(resposta.json()), {'access', 'refresh'})

    def test_senha_errada_retorna_401(self):
        self.assertEqual(self._token(senha='errada').status_code, 401)

    def test_dados_ausentes_retornam_400(self):
        resposta = self.client.post(reverse('jwt_auth:token'), {}, content_type='application/json')

        self.assertEqual(resposta.status_code, 400)

    def test_conta_pendente_retorna_403(self):
        self.usuario.status_conta = self.usuario.StatusConta.PENDENTE
        self.usuario.save()

        self.assertEqual(self._token().status_code, 403)

    def test_rota_protegida_com_bearer(self):
        access = self._token().json()['access']

        resposta = self.client.get(reverse('jwt_auth:usuario_atual'), HTTP_AUTHORIZATION=f'Bearer {access}')

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['tipo_perfil'], 'ong')

    def test_rota_protegida_sem_token_ou_com_refresh_retorna_401(self):
        refresh = self._token().json()['refresh']

        sem_token = self.client.get(reverse('jwt_auth:usuario_atual'))
        com_refresh = self.client.get(reverse('jwt_auth:usuario_atual'), HTTP_AUTHORIZATION=f'Bearer {refresh}')

        self.assertEqual(sem_token.status_code, 401)
        self.assertEqual(com_refresh.status_code, 401)

    def test_renovar_com_refresh_emite_novo_access(self):
        refresh = self._token().json()['refresh']

        resposta = self.client.post(reverse('jwt_auth:renovar_token'), {'refresh': refresh}, content_type='application/json')

        self.assertEqual(resposta.status_code, 200)
        self.assertIn('access', resposta.json())

    @override_settings(JWT_ACCESS_TTL=timedelta(seconds=-1))
    def test_access_expirado_e_recusado(self):
        access = emitir_tokens(self.usuario)['access']

        resposta = self.client.get(reverse('jwt_auth:usuario_atual'), HTTP_AUTHORIZATION=f'Bearer {access}')

        self.assertEqual(resposta.status_code, 401)
