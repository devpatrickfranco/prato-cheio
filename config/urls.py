"""Roteamento principal: cada app declara suas rotas no próprio urls.py.

See https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.auth.urls')),
    path('', include('apps.usuarios.urls')),
    path('', include('apps.metricas.urls')),
    path('', include('apps.lotes.urls')),
]

# Fotos enviadas pelos doadores. Serve direto do MEDIA_ROOT (suficiente para este porte);
# com mais tráfego, entregue /media/ por um servidor web ou armazenamento de objetos.
def servir_media(request, path):
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    re_path(r'^%s(?P<path>.*)$' % settings.MEDIA_URL.lstrip('/'), servir_media),
]
