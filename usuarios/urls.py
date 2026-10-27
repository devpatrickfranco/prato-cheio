from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/pf/', views.login_view, {'perfil': 'pf'}, name='login_pf'),
    path('login/pj/', views.login_view, {'perfil': 'pj'}, name='login_pj'),
    path('login/ong/', views.login_view, {'perfil': 'ong'}, name='login_ong'),
    path('cadastro/pf/', views.cadastro_view, {'perfil': 'pf'}, name='cadastro_pf'),
    path('cadastro/pj/', views.cadastro_view, {'perfil': 'pj'}, name='cadastro_pj'),
    path('cadastro/ong/', views.cadastro_view, {'perfil': 'ong'}, name='cadastro_ong'),
    path('sair/', views.sair, name='sair'),
]
