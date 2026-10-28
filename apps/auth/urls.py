from django.urls import path

from . import views

app_name = 'jwt_auth'

urlpatterns = [
    # Páginas
    path('login/doador/', views.login, {'perfil': 'doador'}, name='login_doador'),
    path('login/consumidor/', views.login, {'perfil': 'consumidor'}, name='login_consumidor'),
    path('login/ong/', views.login, {'perfil': 'ong'}, name='login_ong'),
    path('sair/', views.sair, name='sair'),
    # API JSON
    path('auth/token/', views.obter_token, name='token'),
    path('auth/token/renovar/', views.renovar_token, name='renovar_token'),
    path('auth/eu/', views.usuario_atual, name='usuario_atual'),
]
