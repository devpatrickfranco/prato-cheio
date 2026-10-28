"""Roteamento principal: cada app declara suas rotas no próprio urls.py.

See https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.auth.urls')),
    path('', include('apps.usuarios.urls')),
    path('', include('apps.metricas.urls')),
    path('', include('apps.lotes.urls')),
]
