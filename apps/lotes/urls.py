from django.urls import path

from . import views

app_name = 'lotes'

urlpatterns = [
    # Consumidor e ONG
    path('explore/', views.explorar, name='explorar'),
    path('explore/<int:pk>/reservar/', views.reservar, name='reservar'),
    path('minhas-reservas/', views.minhas_reservas, name='minhas_reservas'),
    path('minhas-reservas/<int:pk>/cancelar/', views.cancelar_reserva, name='cancelar_reserva'),
    # Doador
    path('meus-lotes/', views.meus_lotes, name='meus_lotes'),
    path('meus-lotes/novo/', views.novo_lote, name='novo_lote'),
    path('meus-lotes/<int:pk>/editar/', views.editar_lote, name='editar_lote'),
    path('meus-lotes/<int:pk>/excluir/', views.excluir_lote, name='excluir_lote'),
    path('meus-lotes/<int:pk>/retirada/', views.registrar_retirada, name='registrar_retirada'),
]
