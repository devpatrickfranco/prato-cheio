from django.apps import AppConfig


class AuthConfig(AppConfig):
    name = 'apps.auth'
    # O label 'auth' já pertence a django.contrib.auth.
    label = 'jwt_auth'
    verbose_name = 'Autenticação JWT'
