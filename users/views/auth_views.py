from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from users.services.auth_service import AuthService
from django.contrib.auth import authenticate, login, logout


@csrf_protect
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        service = AuthService()

        user = service.sign_in(username, password)
        if user:
            login(request, user)
            return redirect('main')
        else:
            return render(request, "users/login.html", {'error': 'Invalid username or password'})
    return render(request, "users/login.html")


@csrf_protect
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')

        service = AuthService()

        user = service.sign_up(username, password, email)

        if user:
            login(request, user)
            return redirect('main')
        else:
            return render(request, "users/register.html", {'error': 'Invalid username or password'})
    return render(request, "users/register.html")