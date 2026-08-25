from django.urls import path
from . import views

urlpatterns = [
   path('cadastro/',views.cadastro, name='usuarios'),
   path('login/',views.login, name='usuarios'),
]