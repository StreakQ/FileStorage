from urllib import request

from users.repositories.user_repository import UserRepository
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout


class AuthService:
    def __init__(self):
        self.user_repository = UserRepository()

    def authenticate(self, username, password):
        """Проверяет, существует ли пользователь с таким паролем"""
        user = self.user_repository.get_by_username(username)
        if user and user.check_password(password):
            return user
        return None

    def sign_up(self, username: str, password: str, email: str):
        """Регистрация нового пользователя"""
        user = self.user_repository.create(username=username, password=password, email=email)
        return {"success": True, "user_id": user.id, "username": user.username}

    def sign_in(self, username, password):
        """Вход пользователя в систему"""
        user = self.authenticate(username, password)
        if user:
            auth_login(request, user)
            return True
        return False

    def sign_out(self, username):
        """Выход из системы"""
        user = self.user_repository.get_by_username(username)
        if user:
            logout(request)
