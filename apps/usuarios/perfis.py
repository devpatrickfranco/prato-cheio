"""Perfis de acesso da plataforma, alinhados a Usuario.TipoPerfil."""
from dataclasses import dataclass

from django.urls import reverse


@dataclass(frozen=True)
class Perfil:
    slug: str  # igual ao valor de Usuario.tipo_perfil
    nome: str
    descricao_login: str
    doador: bool = False

    @property
    def url_login(self):
        return f'jwt_auth:login_{self.slug}'

    @property
    def url_painel(self):
        return f'metricas:dashboard_{self.slug}'


PERFIS = {
    'doador': Perfil(
        slug='doador',
        nome='Doador',
        descricao_login='Login para estabelecimentos doadores cadastrarem lotes de alimentos e acompanharem seu impacto na plataforma Prato Cheio.',
        doador=True,
    ),
    'consumidor': Perfil(
        slug='consumidor',
        nome='Consumidor',
        descricao_login='Login para consumidores encontrarem alimentos próximos do vencimento disponíveis para retirada na plataforma Prato Cheio.',
    ),
    'ong': Perfil(
        slug='ong',
        nome='ONG',
        descricao_login='Login para ONGs e instituições reservarem lotes de alimentos doados na plataforma Prato Cheio.',
    ),
}


def url_painel_do_usuario(usuario):
    """Página inicial do usuário logado; administradores vão para o admin."""
    perfil = PERFIS.get(usuario.tipo_perfil)
    return reverse(perfil.url_painel) if perfil else reverse('admin:index')
