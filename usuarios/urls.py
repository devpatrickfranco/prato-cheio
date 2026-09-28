from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/pf/', views.login_pf, name='login_pf'),
    path('login/pj/', views.login_pj, name='login_pj'),
    path('login/ong/', views.login_ong, name='login_ong'),
    path('dashboard/pf/', views.dashboard_pf, name='dashboard_pf'),
    path('dashboard/pj/', views.dashboard_pj, name='dashboard_pj'),
    path('dashboard/ong/', views.dashboard_ong, name='dashboard_ong'),
    path('explore/', views.explore, name='explore'),
    path('meus-lotes/', views.meus_lotes, name='meus_lotes'),
]
