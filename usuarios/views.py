from django.shortcuts import render


def index(request):
    return render(request, 'usuarios/index.html')


def login_pf(request):
    return render(request, 'usuarios/login-pf.html')


def login_pj(request):
    return render(request, 'usuarios/login-pj.html')


def login_ong(request):
    return render(request, 'usuarios/login-ong.html')


def dashboard_pf(request):
    return render(request, 'usuarios/dashboard-pf.html')


def dashboard_pj(request):
    return render(request, 'usuarios/dashboard-pj.html')


def dashboard_ong(request):
    return render(request, 'usuarios/dashboard-ong.html')


def explore(request):
    return render(request, 'usuarios/explore.html')


def meus_lotes(request):
    return render(request, 'usuarios/meus-lotes.html')
