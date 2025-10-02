from django.urls import path
from users.views.users_views import login_view, register_view

app_name = 'users'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
]