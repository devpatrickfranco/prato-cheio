from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


def preencher_dias_de_retirada(apps, schema_editor):
    """Lotes antigos: todos os dias entre o início e o fim da janela de retirada."""
    Lote = apps.get_model('lotes', 'Lote')
    for lote in Lote.objects.all():
        dia = timezone.localtime(lote.retirada_inicio).date()
        ultimo = timezone.localtime(lote.retirada_fim).date()
        dias = []
        while dia <= ultimo:
            dias.append(dia.isoformat())
            dia += timedelta(days=1)
        lote.retirada_dias = dias
        lote.save(update_fields=['retirada_dias'])


class Migration(migrations.Migration):

    dependencies = [
        ('lotes', '0004_lote_foto_alter_reserva_status'),
    ]

    operations = [
        # Os lotes existentes não têm preço, portanto são doações.
        migrations.AddField(
            model_name='lote',
            name='modalidade',
            field=models.CharField(choices=[('doacao', 'Doação'), ('venda', 'Venda')], default='doacao', max_length=6),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='lote',
            name='preco',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='preço'),
        ),
        migrations.AddField(
            model_name='lote',
            name='retirada_dias',
            field=models.JSONField(default=list, verbose_name='dias de retirada'),
        ),
        migrations.AlterField(
            model_name='lote',
            name='peso_kg',
            field=models.DecimalField(decimal_places=3, max_digits=9, verbose_name='peso (kg)'),
        ),
        migrations.AlterField(
            model_name='lote',
            name='unidade',
            field=models.CharField(choices=[('kg', 'kg'), ('un', 'un')], default='un', max_length=2),
        ),
        migrations.AddConstraint(
            model_name='lote',
            constraint=models.CheckConstraint(
                condition=models.Q(('modalidade', 'doacao'), ('preco__isnull', True))
                | models.Q(('modalidade', 'venda'), ('preco__gt', 0), ('preco__isnull', False)),
                name='ck_lote_preco',
            ),
        ),
        migrations.RunPython(preencher_dias_de_retirada, migrations.RunPython.noop),
    ]
