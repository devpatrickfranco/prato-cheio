from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.lotes.models import Alimento, Lote
from apps.usuarios.models import Estabelecimento

SENHA_DEMO = 'prato123demo'

# (email, nome, perfil, (lat, lon)) — coordenadas em Campinas/SP.
USUARIOS = [
    ('mercado@demo.com', 'Supermercado Central', 'doador', None),
    ('padaria@demo.com', 'Padaria Sabor do Trigo', 'doador', None),
    ('bemtevi@demo.com', 'Mercado Bem Te Vi', 'doador', None),
    ('joao@demo.com', 'João Silva', 'consumidor', ('-22.909600', '-47.062600')),
    ('esperanca@demo.com', 'Instituto Esperança', 'ong', ('-22.931000', '-47.074800')),
]

# email do doador: (razão social, CNPJ, tipo, bairro, (lat, lon))
ESTABELECIMENTOS = {
    'mercado@demo.com': ('Supermercado Central LTDA', '11222333000181', 'mercado', 'Centro', ('-22.905600', '-47.060800')),
    'padaria@demo.com': ('Padaria Sabor do Trigo ME', '22333444000172', 'padaria', 'Cambuí', ('-22.893700', '-47.052500')),
    'bemtevi@demo.com': ('Mercado Bem Te Vi EIRELI', '33444555000163', 'mercado', 'Barão Geraldo', ('-22.824100', '-47.078900')),
}

# (doador, descrição, (cod_pof, cod_preparo), quantidade, unidade, peso_kg, dias até vencer, retirada)
LOTES = [
    ('bemtevi@demo.com', 'Kit Hortifruti (Tomates e Cenouras)', (6705101, 99), '15', 'kg', '15', 0, (18, 19)),
    ('padaria@demo.com', 'Pães Artesanais (Misto)', (8001501, 99), '5', 'kg', '5', 1, (8, 9)),
    ('mercado@demo.com', 'Laticínios e Iogurtes', (7901201, 99), '20', 'un', '4', 1, (10, 12)),
]


class Command(BaseCommand):
    help = f'Cria contas e lotes de demonstração (senha de todas as contas: {SENHA_DEMO}).'

    @transaction.atomic
    def handle(self, *args, **options):
        Usuario = get_user_model()
        usuarios = {}
        for email, nome, perfil, coordenadas in USUARIOS:
            usuario, _ = Usuario.objects.update_or_create(
                email=email,
                defaults={
                    'nome': nome, 'tipo_perfil': perfil, 'status_conta': Usuario.StatusConta.APROVADO,
                    'latitude': Decimal(coordenadas[0]) if coordenadas else None,
                    'longitude': Decimal(coordenadas[1]) if coordenadas else None,
                },
            )
            usuario.set_password(SENHA_DEMO)
            usuario.save()
            usuarios[email] = usuario

        estabelecimentos = {}
        for email, (razao, cnpj, tipo, bairro, (lat, lon)) in ESTABELECIMENTOS.items():
            estabelecimentos[email], _ = Estabelecimento.objects.update_or_create(
                usuario=usuarios[email],
                defaults={
                    'razao_social': razao, 'cnpj': cnpj, 'tipo_estabelecimento': tipo, 'cep': '13010100',
                    'logradouro': 'Rua de Demonstração', 'numero': '100', 'bairro': bairro,
                    'cidade': 'Campinas', 'uf': 'SP', 'latitude': Decimal(lat), 'longitude': Decimal(lon),
                },
            )

        hoje = timezone.localdate()
        for email, descricao, (cod_pof, cod_preparo), qtd, unidade, peso, dias, (inicio, fim) in LOTES:
            alimento = Alimento.objects.get(cod_pof=cod_pof, cod_preparo=cod_preparo)
            dia = hoje + timedelta(days=dias)
            Lote.objects.update_or_create(
                estabelecimento=estabelecimentos[email], descricao=descricao,
                defaults={
                    'alimento': alimento, 'categoria': alimento.categoria,
                    'quantidade': Decimal(qtd), 'unidade': unidade, 'peso_kg': Decimal(peso),
                    'data_validade': dia, 'status': Lote.Status.DISPONIVEL,
                    'retirada_inicio': timezone.make_aware(datetime.combine(dia, time(inicio))),
                    'retirada_fim': timezone.make_aware(datetime.combine(dia, time(fim))),
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f'{len(USUARIOS)} contas e {len(LOTES)} lotes de demonstração prontos. Senha: {SENHA_DEMO}'
        ))
