from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from typing import List, Optional
from django.contrib.auth.hashers import check_password


class UserRepository:
    def __init__(self):
        self.User = get_user_model()

    def create(self, **kwargs) -> User:
        username = kwargs.get('username')
        password = kwargs.get('password')
        email = kwargs.get('email')

        if not username or not password or not email:
            raise ValueError("Поля username, password, email должны быть заполнены")

        if self.user_exists(username):
            raise ValueError(f'Пользователь с юзернеймом {username} уже существует')

        if self.User.objects.filter(email=email).exists():
            raise ValueError(f'Пользователь с почтой {email} уже существует')

        user = self.User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        return user

    def get_all(self) -> List[User]:
        return list(self.User.objects.all())

    def get_by_id(self, id: int) -> Optional[User]:
        try:
            return self.User.objects.get(pk=id)
        except self.User.DoesNotExist:
            return None

    def get_by_username(self, username: str) -> Optional[User]:
        try:
            return self.User.objects.get(username=username)
        except self.User.DoesNotExist:
            return None

    def update(self, id: int, **kwargs) -> User:
        user = self.get_by_id(id)
        if not user:
            raise ValueError(f'Пользователь с ID {id} не найден')

        for key, value in kwargs.items():
            if key == 'password' and value:
                user.set_password(value)
            elif key == 'email' and value:
                if self.User.objects.exclude(pk=user.pk).filter(email=value).exists():
                    raise ValueError(f'Email "{value}" уже используется')
                user.email = value
            elif key == 'username' and value:
                if self.user_exists(value) and value != user.username:
                    raise ValueError(f'Username "{value}" уже занят')
                user.username = value
            elif hasattr(user, key):
                setattr(user, key, value)

        user.save()
        return user

    def delete(self, id: int) -> bool:
        user = self.get_by_id(id)
        if user is None:
            return False
        user.delete()
        return True

    def user_exists(self, username: str) -> bool:
        return self.User.objects.filter(username=username).exists()

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        try:
            user = self.User.objects.get(username=username)
            if check_password(password, user.password):
                return user
        except self.User.DoesNotExist:
            return None
