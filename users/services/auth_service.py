from users.repositories.user_repository import UserRepository
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout


class AuthService:
    def __init__(self):
        self.user_repository = UserRepository()

    def sign_up(self, username: str, password: str, email: str):
        """Регистрация нового пользователя"""
        user = self.user_repository.create(username=username, password=password, email=email)
        return user

    def sign_in(self, username, password):
        """Вход пользователя в систему"""
        from django.contrib.auth import authenticate
        user = authenticate(username=username, password=password)
        return user