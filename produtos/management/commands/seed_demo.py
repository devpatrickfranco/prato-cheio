from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from produtos import services
from produtos.models import Categoria, Lote, Reserva
from usuarios.models import Estabelecimento, Usuario

SENHA_PADRAO = 'prato-cheio-123'


class Command(BaseCommand):
    help = 'Cria usuários, lotes e reservas de demonstração (senha padrão: %s).' % SENHA_PADRAO

    def add_arguments(self, parser):
        parser.add_argument('--senha', default=SENHA_PADRAO, help='Senha dos usuários de demonstração.')

    @transaction.atomic
    def handle(self, *args, senha, **opcoes):
        agora = timezone.now()
        hoje = timezone.localdate()
        categoria = {c.nome: c for c in Categoria.objects.all()}

        def usuario(email, nome, perfil, telefone, status=Usuario.Status.APROVADO):
            obj, criado = Usuario.objects.get_or_create(
                email=email,
                defaults={'nome': nome, 'tipo_perfil': perfil, 'telefone': telefone, 'status_conta': status},
            )
            if criado:
                obj.set_password(senha)
                obj.save()
            return obj

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
        joao = usuario('joao@exemplo.com.br', 'João Silva', 'pf', '19999990007')

        e_bom_preco = estabelecimento(
            bom_preco, 'Hortifruti Bom Preço LTDA', '11222333000181', 'hortifruti',
            '13010100', 'Rua Barão de Jaguara', '850', 'Centro')
        e_pao_nosso = estabelecimento(
            pao_nosso, 'Padaria Pão Nosso ME', '22333444000172', 'padaria',
            '13025200', 'Rua Coronel Quirino', '1200', 'Cambuí')
        estabelecimento(
            mesa, 'ONG Mesa Solidária', '33444555000163', 'ong',
            '13076000', 'Avenida Júlio Diniz', '430', 'Taquaral')
        estabelecimento(
            vila, 'Cozinha Comunitária Vila Nova', '44555666000154', 'ong',
            '13050000', 'Rua das Flores', '25', 'Vila Nova')

        if Lote.objects.exists():
            self.stdout.write(self.style.WARNING('Já existem lotes; nada de novo foi criado nos lotes.'))
            return

        def lote(estab, nome_categoria, descricao, qtd, unidade, peso, dias_validade, tipo, preco=None):
            return Lote.objects.create(
                estabelecimento=estab, categoria=categoria[nome_categoria], descricao=descricao,
                quantidade=Decimal(qtd), unidade=unidade, peso_kg=Decimal(peso),
                data_validade=hoje + timedelta(days=dias_validade),
                retirada_inicio=agora + timedelta(hours=1),
                retirada_fim=agora + timedelta(days=max(dias_validade, 1), hours=-1) if dias_validade else agora + timedelta(hours=6),
                tipo=tipo, preco=Decimal(preco) if preco else None,
            )

        # Doações para ONGs (vitrine da ONG)
        lote(e_bom_preco, 'Hortifruti', 'Tomates maduros', '8', 'kg', '8', 2, Lote.Tipo.DOACAO)
        lote(e_bom_preco, 'Laticínio', 'Iogurtes naturais', '12', 'un', '1.2', 3, Lote.Tipo.DOACAO)
        reservado = lote(e_pao_nosso, 'Padaria', 'Pães franceses do dia', '40', 'un', '3.2', 1, Lote.Tipo.DOACAO)
        services.reservar(reservado.pk, vila)

        # Vendas para consumidores (vitrine do consumidor)
        lote(e_bom_preco, 'Hortifruti', 'Kit hortifruti (tomates e cenouras)', '15', 'kg', '15', 1, Lote.Tipo.VENDA, '30.00')
        lote(e_pao_nosso, 'Padaria', 'Pães artesanais (misto)', '5', 'kg', '5', 1, Lote.Tipo.VENDA, '25.00')
        venda = lote(e_bom_preco, 'Hortifruti', 'Bananas maduras em caixa', '20', 'kg', '20', 2, Lote.Tipo.VENDA, '40.00')
        services.reservar(venda.pk, joao)

        # Histórico já retirado, para alimentar os indicadores de impacto
        for descricao, peso, dias_atras, estab, categoria_nome, consumidor in [
            ('Bananas maduras em caixa', '20', 3, e_bom_preco, 'Hortifruti', mesa),
            ('Pães do dia anterior', '6', 40, e_pao_nosso, 'Padaria', mesa),
            ('Frutas variadas', '12', 70, e_bom_preco, 'Hortifruti', vila),
        ]:
            antigo = Lote.objects.create(
                estabelecimento=estab, categoria=categoria[categoria_nome], descricao=descricao,
                quantidade=Decimal(peso), unidade=Lote.Unidade.KG, peso_kg=Decimal(peso),
                data_validade=hoje - timedelta(days=dias_atras - 1),
                retirada_inicio=agora - timedelta(days=dias_atras, hours=3),
                retirada_fim=agora - timedelta(days=dias_atras),
                status=Lote.Status.RETIRADO,
            )
            Reserva.objects.create(
                lote=antigo, usuario=consumidor, status=Reserva.Status.CONFIRMADA,
                data_reserva=agora - timedelta(days=dias_atras, hours=4),
                data_expiracao=antigo.retirada_fim,
                data_confirmacao=agora - timedelta(days=dias_atras, hours=1),
            )

        self.stdout.write(self.style.SUCCESS(
            f'Dados de demonstração criados. Senha de todos os usuários: {senha}\n'
            'Admin: admin@pratocheio.com.br | Doador: contato@bompreco.com.br | '
            'ONG: contato@mesasolidaria.org.br | Consumidor: joao@exemplo.com.br'
        ))
