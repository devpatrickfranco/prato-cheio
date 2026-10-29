from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = 'jwt_auth'

urlpatterns = [
    # Páginas
    path('login/doador/', views.login, {'perfil': 'doador'}, name='login_doador'),
    path('login/consumidor/', views.login, {'perfil': 'consumidor'}, name='login_consumidor'),
    path('login/ong/', views.login, {'perfil': 'ong'}, name='login_ong'),
    path('sair/', views.sair, name='sair'),
    # Recuperação de senha (e-mail com link de uso único)
    path('senha/esqueci/', auth_views.PasswordResetView.as_view(
        template_name='jwt_auth/senha_esqueci.html',
        email_template_name='jwt_auth/email_redefinir_senha.txt',
        subject_template_name='jwt_auth/email_redefinir_senha_assunto.txt',
        success_url=reverse_lazy('jwt_auth:senha_enviada'),
    ), name='senha_esqueci'),
    path('senha/enviada/', auth_views.PasswordResetDoneView.as_view(
        template_name='jwt_auth/senha_enviada.html',
    ), name='senha_enviada'),
    path('senha/redefinir/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='jwt_auth/senha_redefinir.html',
        success_url=reverse_lazy('jwt_auth:senha_redefinida'),
    ), name='senha_redefinir'),
    path('senha/redefinida/', auth_views.PasswordResetCompleteView.as_view(
        template_name='jwt_auth/senha_redefinida.html',
    ), name='senha_redefinida'),
    # API JSON
    path('auth/token/', views.obter_token, name='token'),
    path('auth/token/renovar/', views.renovar_token, name='renovar_token'),
    path('auth/token/revogar/', views.revogar_token, name='revogar_token'),
    path('auth/eu/', views.usuario_atual, name='usuario_atual'),
]
