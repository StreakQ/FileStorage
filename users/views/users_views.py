from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import authenticate, login, logout


@csrf_protect
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        from users.services.auth_service import AuthService
        service = AuthService()

        user = service.sign_in(username, password)
        if user is not None:
            login(request, user)
            return redirect('files:file_manager')
        else:
            return render(request, "users/login.html", {'error': 'Invalid username or password'})
    return render(request, "users/login.html")


@csrf_protect
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')

        from users.services.auth_service import AuthService
        service = AuthService()

        try:
            user = service.sign_up(username, password, email)

            login(request, user)
            return redirect('files:file_manager')

        except Exception as e:
            return render(request, "users/register.html", {'error': str(e)})
    return render(request, "users/register.html")


def logout_view(request):
    logout(request)
    return redirect('users:login')


def home_view(request):
    """
    Главная страница сайта

    Для неаутентифицированных пользователей показывает форму входа/регистрации
    Для аутентифицированных перенаправляет в файловый менеджер
    """
    if request.user.is_authenticated:
        return redirect('files:file_manager')
    else:
        return render(request, "users/welcome.html")