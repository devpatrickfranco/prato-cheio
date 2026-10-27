from django.urls import path

from . import views

app_name = 'metricas'

urlpatterns = [
    path('painel/', views.painel, name='painel'),
    path('relatorio/', views.relatorio, name='relatorio'),
]
