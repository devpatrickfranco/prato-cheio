from django.urls import path

from . import views

app_name = 'produtos'

urlpatterns = [
    path('explorar/', views.explorar, name='explorar'),
    path('lotes/<int:lote_id>/reservar/', views.reservar_lote, name='reservar_lote'),
    path('reservas/', views.minhas_reservas, name='minhas_reservas'),
    path('reservas/<int:reserva_id>/cancelar/', views.cancelar_reserva, name='cancelar_reserva'),
    path('meus-lotes/', views.meus_lotes, name='meus_lotes'),
    path('meus-lotes/novo/', views.lote_novo, name='lote_novo'),
    path('meus-lotes/<int:lote_id>/editar/', views.lote_editar, name='lote_editar'),
    path('meus-lotes/<int:lote_id>/remover/', views.lote_remover, name='lote_remover'),
    path('reservas/<int:reserva_id>/confirmar/', views.confirmar_retirada, name='confirmar_retirada'),
    path('reservas/<int:reserva_id>/nao-retirado/', views.nao_retirado, name='nao_retirado'),
]
