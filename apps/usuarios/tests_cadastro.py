from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.auth.cookies import ACCESS_COOKIE
from apps.auth.tokens import emitir_access

from . import geocodificacao
from .models import Estabelecimento
from .validators import cnpj_valido, cpf_valido

SENHA = 'Senha-forte-123'
CNPJ_VALIDO = '11222333000181'
CPF_VALIDO = '52998224725'
CAMPINAS = (Decimal('-22.905600'), Decimal('-47.060800'))

ESTABELECIMENTO = {
    'razao_social': 'Mercado Novo LTDA', 'cnpj': '11.222.333/0001-81', 'tipo_estabelecimento': 'mercado',
    'cep': '13010-100', 'logradouro': 'Rua Barão de Jaguara', 'numero': '10', 'bairro': 'Centro',
    'cidade': 'Campinas', 'uf': 'sp',
}


def _dados_base(**extra):
    dados = {'nome': 'Maria Souza', 'email': 'maria@exemplo.com', 'telefone': '19999990000', 'senha': SENHA, 'confirmar_senha': SENHA}
    dados.update(extra)
    return dados


class ValidadoresTests(SimpleTestCase):
    def test_cpf(self):
        self.assertTrue(cpf_valido(CPF_VALIDO))
        self.assertFalse(cpf_valido('52998224726'))
        self.assertFalse(cpf_valido('11111111111'))
        self.assertFalse(cpf_valido('123'))

    def test_cnpj(self):
        self.assertTrue(cnpj_valido(CNPJ_VALIDO))
        self.assertFalse(cnpj_valido('11222333000182'))
        self.assertFalse(cnpj_valido('00000000000000'))


class CadastroTests(TestCase):
    def _cadastrar(self, perfil, **extra):
        return self.client.post(reverse(f'usuarios:cadastro_{perfil}'), _dados_base(**extra))

    def test_paginas_de_cadastro_dos_tres_perfis(self):
        for perfil, rotulo in (('doador', 'Cadastro Doador'), ('consumidor', 'CPF'), ('ong', 'CNPJ')):
            with self.subTest(perfil=perfil):
                resposta = self.client.get(reverse(f'usuarios:cadastro_{perfil}'))

                self.assertEqual(resposta.status_code, 200)
                self.assertContains(resposta, rotulo)
                self.assertContains(resposta, 'data-resumo-erros')

    def test_login_linka_para_cadastro_e_recuperacao_de_senha(self):
        resposta = self.client.get(reverse('jwt_auth:login_ong'))

        self.assertContains(resposta, f'href="{reverse("usuarios:cadastro_ong")}"')
        self.assertContains(resposta, f'href="{reverse("jwt_auth:senha_esqueci")}"')

    def test_consumidor_nasce_pendente_e_nao_entra(self):
        resposta = self._cadastrar('consumidor', documento='529.982.247-25')

        self.assertRedirects(resposta, reverse('jwt_auth:login_consumidor'))
        usuario = get_user_model().objects.get(email='maria@exemplo.com')
        self.assertEqual(usuario.status_conta, 'pendente')
        self.assertEqual((usuario.tipo_perfil, usuario.documento), ('consumidor', CPF_VALIDO))
        self.assertTrue(usuario.check_password(SENHA))
        login = self.client.post(reverse('jwt_auth:login_consumidor'), {'email': 'maria@exemplo.com', 'senha': SENHA})
        self.assertContains(login, 'ainda não foi aprovada')

    def test_apos_aprovacao_o_usuario_entra(self):
        self._cadastrar('ong', documento=CNPJ_VALIDO)
        get_user_model().objects.update(status_conta='aprovado')

        login = self.client.post(reverse('jwt_auth:login_ong'), {'email': 'maria@exemplo.com', 'senha': SENHA})

        self.assertRedirects(login, reverse('metricas:dashboard_ong'))

    def test_mensagem_de_sucesso_aparece_no_login(self):
        resposta = self.client.post(
            reverse('usuarios:cadastro_consumidor'), _dados_base(documento=CPF_VALIDO), follow=True,
        )

        self.assertContains(resposta, 'Cadastro enviado!')

    def test_doador_cria_usuario_e_estabelecimento(self):
        with mock.patch('apps.usuarios.views.geocodificar', return_value=CAMPINAS):
            resposta = self.client.post(reverse('usuarios:cadastro_doador'), {**_dados_base(), **ESTABELECIMENTO})

        self.assertRedirects(resposta, reverse('jwt_auth:login_doador'))
        estabelecimento = Estabelecimento.objects.get()
        self.assertEqual(estabelecimento.usuario.email, 'maria@exemplo.com')
        self.assertEqual((estabelecimento.cnpj, estabelecimento.cep, estabelecimento.uf), (CNPJ_VALIDO, '13010100', 'SP'))
        self.assertEqual((estabelecimento.latitude, estabelecimento.longitude), CAMPINAS)

    def test_geocodificacao_falha_nao_impede_o_cadastro(self):
        with mock.patch('apps.usuarios.views.geocodificar', return_value=None):
            self.client.post(reverse('usuarios:cadastro_doador'), {**_dados_base(), **ESTABELECIMENTO})

        estabelecimento = Estabelecimento.objects.get()
        self.assertIsNone(estabelecimento.latitude)

    def test_cep_do_consumidor_define_o_ponto_de_referencia(self):
        with mock.patch('apps.usuarios.views.geocodificar', return_value=CAMPINAS) as geo:
            self._cadastrar('consumidor', documento=CPF_VALIDO, cep='13010-100')

        geo.assert_called_once_with(cep='13010100')
        usuario = get_user_model().objects.get()
        self.assertEqual((usuario.latitude, usuario.longitude), CAMPINAS)

    def test_validacoes_do_cadastro(self):
        get_user_model().objects.create_user(email='existe@exemplo.com', password='x', nome='X', tipo_perfil='ong', documento=CNPJ_VALIDO)
        casos = {
            'documento': dict(documento='111.111.111-11'),
            'email': dict(documento=CPF_VALIDO, email='EXISTE@exemplo.com'),
            'confirmar_senha': dict(documento=CPF_VALIDO, confirmar_senha='outra'),
            'senha': dict(documento=CPF_VALIDO, senha='123', confirmar_senha='123'),
            'cep': dict(documento=CPF_VALIDO, cep='123'),
        }
        for campo, extra in casos.items():
            with self.subTest(campo=campo):
                resposta = self._cadastrar('consumidor', **extra)

                self.assertEqual(resposta.status_code, 200)
                self.assertIn(campo, resposta.context['form'].errors)
                self.assertContains(resposta, 'data-resumo-servidor')
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_cnpj_de_ong_duplicado_e_recusado(self):
        get_user_model().objects.create_user(email='existe@exemplo.com', password='x', nome='X', tipo_perfil='ong', documento=CNPJ_VALIDO)

        resposta = self._cadastrar('ong', documento=CNPJ_VALIDO)

        self.assertContains(resposta, 'já está cadastrado')

    def test_cnpj_de_estabelecimento_duplicado_e_invalido_sao_recusados(self):
        url = reverse('usuarios:cadastro_doador')
        with mock.patch('apps.usuarios.views.geocodificar', return_value=None):
            self.client.post(url, {**_dados_base(), **ESTABELECIMENTO})
            duplicado = self.client.post(url, {**_dados_base(email='outro@exemplo.com'), **ESTABELECIMENTO})
            invalido = self.client.post(url, {**_dados_base(email='outro@exemplo.com'), **ESTABELECIMENTO, 'cnpj': '11222333000199'})

        self.assertContains(duplicado, 'já está cadastrado')
        self.assertContains(invalido, 'CNPJ válido')
        self.assertEqual(Estabelecimento.objects.count(), 1)

    def test_conta_recusada_ve_mensagem_propria(self):
        get_user_model().objects.create_user(
            email='nao@exemplo.com', password=SENHA, nome='Não', tipo_perfil='consumidor', status_conta='recusado',
        )

        resposta = self.client.post(reverse('jwt_auth:login_consumidor'), {'email': 'nao@exemplo.com', 'senha': SENHA})

        self.assertContains(resposta, 'cadastro foi recusado')


class MeuEstabelecimentoTests(TestCase):
    def setUp(self):
        self.doador = get_user_model().objects.create_user(
            email='d@exemplo.com', password='x', nome='Doador', tipo_perfil='doador', status_conta='aprovado',
        )
        self.client.cookies[ACCESS_COOKIE] = emitir_access(self.doador)

    def test_cria_estabelecimento_e_geocodifica(self):
        with mock.patch('apps.usuarios.views.geocodificar', return_value=CAMPINAS):
            resposta = self.client.post(reverse('usuarios:meu_estabelecimento'), ESTABELECIMENTO)

        self.assertRedirects(resposta, reverse('usuarios:meu_estabelecimento'))
        estabelecimento = Estabelecimento.objects.get(usuario=self.doador)
        self.assertEqual(estabelecimento.latitude, CAMPINAS[0])

    def test_edita_sem_regeocodificar_quando_o_endereco_nao_muda(self):
        with mock.patch('apps.usuarios.views.geocodificar', return_value=CAMPINAS):
            self.client.post(reverse('usuarios:meu_estabelecimento'), ESTABELECIMENTO)
        with mock.patch('apps.usuarios.views.geocodificar') as geo:
            self.client.post(reverse('usuarios:meu_estabelecimento'), {**ESTABELECIMENTO, 'razao_social': 'Novo nome'})

        geo.assert_not_called()
        self.assertEqual(Estabelecimento.objects.get().razao_social, 'Novo nome')

    def test_regeocodifica_quando_o_endereco_muda(self):
        with mock.patch('apps.usuarios.views.geocodificar', return_value=CAMPINAS):
            self.client.post(reverse('usuarios:meu_estabelecimento'), ESTABELECIMENTO)
        outra = (Decimal('-22.9'), Decimal('-47.1'))
        with mock.patch('apps.usuarios.views.geocodificar', return_value=outra) as geo:
            self.client.post(reverse('usuarios:meu_estabelecimento'), {**ESTABELECIMENTO, 'numero': '99'})

        geo.assert_called_once()
        self.assertEqual(Estabelecimento.objects.get().latitude, outra[0])

    def test_pagina_avisa_quando_nao_ha_coordenadas(self):
        with mock.patch('apps.usuarios.views.geocodificar', return_value=None):
            self.client.post(reverse('usuarios:meu_estabelecimento'), ESTABELECIMENTO)

        resposta = self.client.get(reverse('usuarios:meu_estabelecimento'))

        self.assertContains(resposta, 'Não foi possível localizar o endereço')

    def test_so_doador_acessa(self):
        consumidor = get_user_model().objects.create_user(
            email='c@exemplo.com', password='x', nome='C', tipo_perfil='consumidor', status_conta='aprovado',
        )
        self.client.cookies[ACCESS_COOKIE] = emitir_access(consumidor)

        resposta = self.client.get(reverse('usuarios:meu_estabelecimento'))

        self.assertRedirects(resposta, reverse('metricas:dashboard_consumidor'))

    def test_menu_do_doador_tem_o_link(self):
        resposta = self.client.get(reverse('usuarios:meu_estabelecimento'))

        self.assertContains(resposta, 'Meu Estabelecimento')


class GeocodificacaoTests(SimpleTestCase):
    def _resposta(self, corpo):
        resposta = mock.MagicMock()
        resposta.__enter__.return_value = resposta
        resposta.read.return_value = corpo
        return resposta

    @override_settings(GEOCODIFICACAO_ATIVA=False)
    def test_desligada_nao_acessa_a_rede(self):
        with mock.patch.object(geocodificacao, 'urlopen') as urlopen:
            self.assertIsNone(geocodificacao.geocodificar(cidade='Campinas', uf='SP'))

        urlopen.assert_not_called()

    @override_settings(GEOCODIFICACAO_ATIVA=True)
    def test_devolve_coordenadas_do_primeiro_resultado(self):
        corpo = b'[{"lat": "-22.9056391", "lon": "-47.0608"}]'
        with mock.patch.object(geocodificacao, 'urlopen', return_value=self._resposta(corpo)):
            coordenadas = geocodificacao.geocodificar(cidade='Campinas', uf='SP', cep='13010100', logradouro='Rua A', numero='1')

        self.assertEqual(coordenadas, (Decimal('-22.905639'), Decimal('-47.060800')))

    @override_settings(GEOCODIFICACAO_ATIVA=True)
    def test_tenta_consultas_menos_especificas_ate_achar(self):
        respostas = [self._resposta(b'[]'), self._resposta(b'[]'), self._resposta(b'[{"lat": "-22.9", "lon": "-47.1"}]')]
        with mock.patch.object(geocodificacao, 'urlopen', side_effect=respostas) as urlopen:
            coordenadas = geocodificacao.geocodificar(cidade='Campinas', uf='SP', cep='13010100', logradouro='Rua A')

        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(coordenadas, (Decimal('-22.900000'), Decimal('-47.100000')))

    @override_settings(GEOCODIFICACAO_ATIVA=True)
    def test_falha_de_rede_ou_resposta_ruim_devolve_none(self):
        for efeito in (OSError('sem rede'), ValueError('json ruim')):
            with self.subTest(efeito=efeito), mock.patch.object(geocodificacao, 'urlopen', side_effect=efeito):
                self.assertIsNone(geocodificacao.geocodificar(cidade='Campinas', uf='SP'))

    @override_settings(GEOCODIFICACAO_ATIVA=True)
    def test_resposta_json_valida_mas_sem_chaves_devolve_none(self):
        with mock.patch.object(geocodificacao, 'urlopen', return_value=self._resposta(b'[{"x": 1}]')):
            self.assertIsNone(geocodificacao.geocodificar(cidade='Campinas', uf='SP'))
