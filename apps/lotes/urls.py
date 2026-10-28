from django.urls import path

from . import views

app_name = 'lotes'

urlpatterns = [
    path('explore/', views.explorar, name='explorar'),
    path('meus-lotes/', views.meus_lotes, name='meus_lotes'),
    path('meus-lotes/novo/', views.novo_lote, name='novo_lote'),
    path('meus-lotes/<int:pk>/editar/', views.editar_lote, name='editar_lote'),
]
