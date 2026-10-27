from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from . import tokens
from .models import Estabelecimento, Usuario
from .validators import validar_cnpj

SENHA = 'senha-forte-123'
CNPJ_VALIDO = '11222333000181'


def criar_usuario(email, perfil=Usuario.Perfil.PF, status=Usuario.Status.APROVADO, nome='Fulano'):
    return Usuario.objects.create_user(
        email, SENHA, nome=nome, tipo_perfil=perfil, status_conta=status, telefone='19999990000'
    )


def criar_doador(email='doador@exemplo.com', nome='Mercado Teste', cnpj=CNPJ_VALIDO):
    usuario = criar_usuario(email, Usuario.Perfil.PJ, nome=nome)
    Estabelecimento.objects.create(
        usuario=usuario, razao_social=f'{nome} LTDA', cnpj=cnpj, tipo_estabelecimento='mercado',
        cep='13010100', logradouro='Rua A', numero='1', bairro='Centro', cidade='Campinas', uf='SP',
    )
    return usuario


class ValidadoresTests(TestCase):
    def test_cnpj_valido_passa(self):
        validar_cnpj('11.222.333/0001-81')

    def test_cnpj_com_digito_errado_falha(self):
        with self.assertRaises(Exception):
            validar_cnpj('11222333000182')

    def test_cnpj_repetido_falha(self):
        with self.assertRaises(Exception):
            validar_cnpj('11111111111111')


class CadastroTests(TestCase):
    def test_consumidor_nasce_aprovado(self):
        resposta = self.client.post(reverse('usuarios:cadastro_pf'), {
            'nome': 'Maria Souza', 'email': 'Maria@Exemplo.com', 'telefone': '(19) 99999-0000',
            'senha': SENHA, 'confirmar_senha': SENHA,
        })
        self.assertRedirects(resposta, reverse('usuarios:login_pf'))
        usuario = Usuario.objects.get(email='maria@exemplo.com')
        self.assertEqual(usuario.status_conta, Usuario.Status.APROVADO)
        self.assertEqual(usuario.telefone, '19999990000')
        self.assertTrue(usuario.check_password(SENHA))

    def test_doador_nasce_pendente_com_estabelecimento(self):
        resposta = self.client.post(reverse('usuarios:cadastro_pj'), {
            'nome': 'Mercado Sol', 'email': 'sol@exemplo.com', 'telefone': '1933334444',
            'senha': SENHA, 'confirmar_senha': SENHA,
            'razao_social': 'Mercado Sol LTDA', 'cnpj': '11.222.333/0001-81',
            'tipo_estabelecimento': 'mercado', 'cep': '13010-100', 'logradouro': 'Rua A',
            'numero': '10', 'bairro': 'Centro', 'cidade': 'Campinas', 'uf': 'SP',
        })
        self.assertRedirects(resposta, reverse('usuarios:login_pj'))
        usuario = Usuario.objects.get(email='sol@exemplo.com')
        self.assertEqual(usuario.status_conta, Usuario.Status.PENDENTE)
        self.assertEqual(usuario.estabelecimento.cnpj, CNPJ_VALIDO)
        self.assertEqual(usuario.estabelecimento.cep, '13010100')

    def test_ong_recebe_tipo_ong_automaticamente(self):
        self.client.post(reverse('usuarios:cadastro_ong'), {
            'nome': 'ONG Esperança', 'email': 'ong@exemplo.com', 'telefone': '1933334444',
            'senha': SENHA, 'confirmar_senha': SENHA,
            'razao_social': 'Instituto Esperança', 'cnpj': CNPJ_VALIDO, 'cep': '13010100',
            'logradouro': 'Rua B', 'numero': '2', 'bairro': 'Cambuí', 'cidade': 'Campinas', 'uf': 'SP',
        })
        usuario = Usuario.objects.get(email='ong@exemplo.com')
        self.assertEqual(usuario.estabelecimento.tipo_estabelecimento, 'ong')

    def test_cnpj_invalido_nao_cria_conta(self):
        resposta = self.client.post(reverse('usuarios:cadastro_pj'), {
            'nome': 'X', 'email': 'x@exemplo.com', 'telefone': '1933334444',
            'senha': SENHA, 'confirmar_senha': SENHA, 'razao_social': 'X', 'cnpj': '123',
            'tipo_estabelecimento': 'mercado', 'cep': '13010100', 'logradouro': 'R',
            'numero': '1', 'bairro': 'B', 'cidade': 'C', 'uf': 'SP',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email='x@exemplo.com').exists())

    def test_senhas_diferentes_sao_recusadas(self):
        resposta = self.client.post(reverse('usuarios:cadastro_pf'), {
            'nome': 'Ana', 'email': 'ana@exemplo.com', 'telefone': '1933334444',
            'senha': SENHA, 'confirmar_senha': 'outra-senha-123',
        })
        self.assertContains(resposta, 'As senhas não coincidem.')
        self.assertFalse(Usuario.objects.filter(email='ana@exemplo.com').exists())

    def test_email_duplicado_e_recusado(self):
        criar_usuario('repetido@exemplo.com')
        resposta = self.client.post(reverse('usuarios:cadastro_pf'), {
            'nome': 'Outro', 'email': 'REPETIDO@exemplo.com', 'telefone': '1933334444',
            'senha': SENHA, 'confirmar_senha': SENHA,
        })
        self.assertContains(resposta, 'Já existe uma conta com este e-mail.')


class LoginTests(TestCase):
    def setUp(self):
        self.usuario = criar_usuario('pf@exemplo.com')

    def login(self, email='pf@exemplo.com', senha=SENHA, rota='usuarios:login_pf'):
        return self.client.post(reverse(rota), {'email': email, 'senha': senha})

    def test_login_valido_grava_cookies_httponly(self):
        resposta = self.login()
        self.assertRedirects(resposta, reverse('metricas:painel'), fetch_redirect_response=False)
        for nome in (settings.JWT_COOKIE_ACCESS, settings.JWT_COOKIE_REFRESH):
            self.assertTrue(resposta.cookies[nome]['httponly'])
            self.assertEqual(resposta.cookies[nome]['samesite'], 'Lax')

    def test_senha_errada_nao_autentica(self):
        resposta = self.login(senha='errada')
        self.assertContains(resposta, 'E-mail ou senha incorretos para este perfil.')
        self.assertNotIn(settings.JWT_COOKIE_ACCESS, resposta.cookies)

    def test_perfil_errado_nao_autentica(self):
        resposta = self.login(rota='usuarios:login_ong')
        self.assertContains(resposta, 'E-mail ou senha incorretos para este perfil.')

    def test_conta_pendente_nao_entra(self):
        criar_usuario('novo@exemplo.com', status=Usuario.Status.PENDENTE)
        resposta = self.login(email='novo@exemplo.com')
        self.assertContains(resposta, 'ainda está em análise')
        self.assertNotIn(settings.JWT_COOKIE_ACCESS, resposta.cookies)

    def test_bloqueia_apos_tentativas_repetidas(self):
        from django.core.cache import cache
        cache.clear()
        for _ in range(5):
            self.login(senha='errada')
        resposta = self.login()  # mesmo com a senha certa
        self.assertContains(resposta, 'Muitas tentativas')
        cache.clear()

    def test_logout_apaga_cookies_e_exige_post(self):
        self.login()
        self.assertEqual(self.client.get(reverse('usuarios:sair')).status_code, 405)
        resposta = self.client.post(reverse('usuarios:sair'))
        self.assertRedirects(resposta, reverse('usuarios:index'), fetch_redirect_response=False)
        self.assertEqual(resposta.cookies[settings.JWT_COOKIE_ACCESS].value, '')
        self.assertEqual(resposta.cookies[settings.JWT_COOKIE_REFRESH].value, '')
        self.assertRedirects(
            self.client.get(reverse('metricas:painel')), reverse('usuarios:index'),
            fetch_redirect_response=False,
        )


class JWTTests(TestCase):
    def setUp(self):
        self.usuario = criar_usuario('jwt@exemplo.com')

    def test_token_tem_as_claims_esperadas(self):
        carga = tokens.decodificar_token(tokens.gerar_token(self.usuario, tokens.ACCESS), tokens.ACCESS)
        self.assertEqual(carga['sub'], str(self.usuario.pk))
        self.assertEqual(carga['perfil'], 'pf')
        self.assertEqual(carga['tipo'], 'access')

    def test_refresh_nao_vale_como_access(self):
        refresh = tokens.gerar_token(self.usuario, tokens.REFRESH)
        self.assertIsNone(tokens.decodificar_token(refresh, tokens.ACCESS))

    def test_token_adulterado_e_recusado(self):
        token = tokens.gerar_token(self.usuario, tokens.ACCESS)
        self.assertIsNone(tokens.decodificar_token(token[:-2] + 'xx', tokens.ACCESS))

    def test_token_assinado_com_outra_chave_e_recusado(self):
        falso = jwt.encode(
            {'sub': str(self.usuario.pk), 'tipo': 'access', 'iat': datetime.now(timezone.utc),
             'exp': datetime.now(timezone.utc) + timedelta(minutes=5)},
            'chave-do-atacante-com-32-caracteres!!', algorithm='HS256',
        )
        self.assertIsNone(tokens.decodificar_token(falso, tokens.ACCESS))

    def test_token_expirado_e_recusado(self):
        expirado = jwt.encode(
            {'sub': str(self.usuario.pk), 'tipo': 'access',
             'iat': datetime.now(timezone.utc) - timedelta(hours=2),
             'exp': datetime.now(timezone.utc) - timedelta(hours=1)},
            settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
        )
        self.assertIsNone(tokens.decodificar_token(expirado, tokens.ACCESS))

    def test_refresh_valido_renova_o_access_expirado(self):
        self.client.cookies[settings.JWT_COOKIE_REFRESH] = tokens.gerar_token(self.usuario, tokens.REFRESH)
        resposta = self.client.get(reverse('metricas:painel'))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(settings.JWT_COOKIE_ACCESS, resposta.cookies)

    def test_conta_recusada_perde_acesso_mesmo_com_token_valido(self):
        self.client.cookies[settings.JWT_COOKIE_ACCESS] = tokens.gerar_token(self.usuario, tokens.ACCESS)
        self.usuario.status_conta = Usuario.Status.RECUSADO
        self.usuario.save()
        self.assertRedirects(
            self.client.get(reverse('metricas:painel')), reverse('usuarios:index'),
            fetch_redirect_response=False,
        )

    def test_rota_protegida_sem_login_redireciona(self):
        self.assertRedirects(
            self.client.get(reverse('produtos:explorar')), reverse('usuarios:index'),
            fetch_redirect_response=False,
        )

    def test_perfil_sem_permissao_volta_ao_painel(self):
        self.client.cookies[settings.JWT_COOKIE_ACCESS] = tokens.gerar_token(self.usuario, tokens.ACCESS)
        resposta = self.client.get(reverse('produtos:meus_lotes'))  # so para doador (PJ)
        self.assertRedirects(resposta, reverse('metricas:painel'), fetch_redirect_response=False)


class PaginasTests(TestCase):
    """Cada página precisa de título e descrição próprios, um único h1 e um main."""

    def test_titulos_e_descricoes_sao_unicos(self):
        rotas = [
            'usuarios:index', 'usuarios:login_pf', 'usuarios:login_pj', 'usuarios:login_ong',
            'usuarios:cadastro_pf', 'usuarios:cadastro_pj', 'usuarios:cadastro_ong',
        ]
        titulos, descricoes = set(), set()
        for rota in rotas:
            html = self.client.get(reverse(rota)).content.decode()
            self.assertEqual(html.count('<h1'), 1, rota)
            self.assertEqual(html.count('<main'), 1, rota)
            self.assertIn('<html lang="pt-br">', html)
            titulos.add(html.split('<title>')[1].split('</title>')[0])
            descricoes.add(html.split('name="description" content="')[1].split('"')[0])
        self.assertEqual(len(titulos), len(rotas))
        self.assertEqual(len(descricoes), len(rotas))

    def test_descricoes_tem_ate_160_caracteres(self):
        for rota in ['usuarios:index', 'usuarios:login_pf', 'usuarios:cadastro_pj']:
            html = self.client.get(reverse(rota)).content.decode()
            descricao = html.split('name="description" content="')[1].split('"')[0]
            self.assertLessEqual(len(descricao), 160, rota)
