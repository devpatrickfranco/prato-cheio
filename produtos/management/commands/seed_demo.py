from django.core.management.base import BaseCommand
from django.db import transaction

from usuarios.models import Estabelecimento, Usuario

SENHA_PADRAO = 'prato-cheio-123'


class Command(BaseCommand):
    help = 'Cria os usuários de demonstração, um de cada perfil (senha padrão: %s).' % SENHA_PADRAO

    def add_arguments(self, parser):
        parser.add_argument('--senha', default=SENHA_PADRAO, help='Senha dos usuários de demonstração.')

    @transaction.atomic
    def handle(self, *args, senha, **opcoes):
        # Cria o usuário só se ainda não existir, para o comando poder rodar mais de uma vez
        def usuario(email, nome, perfil, telefone, status=Usuario.Status.APROVADO):
            obj, criado = Usuario.objects.get_or_create(
                email=email,
                defaults={'nome': nome, 'tipo_perfil': perfil, 'telefone': telefone, 'status_conta': status},
            )
            if criado:
                obj.set_password(senha)
                obj.save()
            return obj

        # Dados da pessoa jurídica (PJ ou ONG) e o endereço usado no filtro por bairro
        def estabelecimento(user, razao, cnpj, tipo, cep, rua, numero, bairro):
            obj, _ = Estabelecimento.objects.get_or_create(
                usuario=user,
                defaults=dict(
                    razao_social=razao, cnpj=cnpj, tipo_estabelecimento=tipo, cep=cep,
                    logradouro=rua, numero=numero, bairro=bairro, cidade='Campinas', uf='SP',
                ),
            )
            return obj

        if not Usuario.objects.filter(email='admin@pratocheio.com.br').exists():
            Usuario.objects.create_superuser('admin@pratocheio.com.br', senha, nome='Equipe Prato Cheio')

        bom_preco = usuario('contato@bompreco.com.br', 'Hortifruti Bom Preço', 'pj', '19999990002')
        pao_nosso = usuario('contato@paonosso.com.br', 'Padaria Pão Nosso', 'pj', '19999990003')
        usuario('contato@novodia.com.br', 'Mercado Novo Dia', 'pj', '19999990006', Usuario.Status.PENDENTE)
        mesa = usuario('contato@mesasolidaria.org.br', 'ONG Mesa Solidária', 'ong', '19999990004')
        vila = usuario('cozinha@vilanova.org.br', 'Cozinha Comunitária Vila Nova', 'ong', '19999990005')
        usuario('joao@exemplo.com.br', 'João Silva', 'pf', '19999990007')

        estabelecimento(
            bom_preco, 'Hortifruti Bom Preço LTDA', '11222333000181', 'hortifruti',
            '13010100', 'Rua Barão de Jaguara', '850', 'Centro')
        estabelecimento(
            pao_nosso, 'Padaria Pão Nosso ME', '22333444000172', 'padaria',
            '13025200', 'Rua Coronel Quirino', '1200', 'Cambuí')
        estabelecimento(
            mesa, 'ONG Mesa Solidária', '33444555000163', 'ong',
            '13076000', 'Avenida Júlio Diniz', '430', 'Taquaral')
        estabelecimento(
            vila, 'Cozinha Comunitária Vila Nova', '44555666000154', 'ong',
            '13050000', 'Rua das Flores', '25', 'Vila Nova')

        self.stdout.write(self.style.SUCCESS(f'Usuários de demonstração prontos. Senha: {senha}'))
