from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.index, name='index'),
    path('cadastro/doador/', views.cadastro, {'perfil': 'doador'}, name='cadastro_doador'),
    path('cadastro/consumidor/', views.cadastro, {'perfil': 'consumidor'}, name='cadastro_consumidor'),
    path('cadastro/ong/', views.cadastro, {'perfil': 'ong'}, name='cadastro_ong'),
    path('meu-estabelecimento/', views.meu_estabelecimento, name='meu_estabelecimento'),
]
