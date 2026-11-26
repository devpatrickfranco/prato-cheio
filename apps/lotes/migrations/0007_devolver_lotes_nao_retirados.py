from django.db import migrations
from django.utils import timezone


def devolver_lotes(apps, schema_editor):
    """Lotes parados em `nao_retirado` voltam à vitrine se ainda estão na validade; vencidos expiram."""
    Lote = apps.get_model('lotes', 'Lote')
    hoje = timezone.localdate()
    parados = Lote.objects.filter(status='nao_retirado')
    parados.filter(data_validade__gte=hoje).update(status='disponivel')
    parados.filter(data_validade__lt=hoje).update(status='expirado')


class Migration(migrations.Migration):

    dependencies = [
        ('lotes', '0006_peso_opcional'),
    ]

    operations = [
        # Sem volta: não dá para saber quais lotes disponíveis já foram "não retirados".
        migrations.RunPython(devolver_lotes, migrations.RunPython.noop),
    ]
