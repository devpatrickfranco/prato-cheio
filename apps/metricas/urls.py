from django.urls import path

from . import views

app_name = 'metricas'

urlpatterns = [
    path('dashboard/consumidor/', views.painel, {'perfil': 'consumidor'}, name='dashboard_consumidor'),
    path('dashboard/doador/', views.painel, {'perfil': 'doador'}, name='dashboard_doador'),
    path('dashboard/ong/', views.painel, {'perfil': 'ong'}, name='dashboard_ong'),
]
