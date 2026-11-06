from django.apps import AppConfig
from django.db.models import fields


class UsuariosConfig(AppConfig):
    name = 'apps.usuarios'
    verbose_name = 'Usuários'

    def ready(self):
        # O Django 6.1 não traz tradução para o rótulo vazio dos selects ("- Select an option -").
        fields.BLANK_CHOICE_LABEL = 'Selecione'
