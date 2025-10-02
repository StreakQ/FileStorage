from django.urls import path
from .views.files_views import file_manager_view

app_name = 'files'

urlpatterns = [
     path('manager/', file_manager_view, name='file_manager'),

]