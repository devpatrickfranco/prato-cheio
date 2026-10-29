from django.core.management.base import BaseCommand

from apps.lotes import services


class Command(BaseCommand):
    help = (
        'Expira reservas vencidas (o lote volta a disponível) e marca como expirados os lotes '
        'disponíveis com validade vencida. Agende (cron) a cada poucos minutos; as telas também '
        'aplicam essa regra ao listar lotes.'
    )

    def handle(self, *args, **options):
        reservas, lotes = services.atualizar_pendencias()
        self.stdout.write(self.style.SUCCESS(f'{reservas} reserva(s) expirada(s); {lotes} lote(s) expirado(s).'))
