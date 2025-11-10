from django.urls import path
from .views.files_views import *

app_name = 'files'

urlpatterns = [
     path('', home_redirect_view, name='home'),
     path('manager/', file_manager_view, name='file_manager'),
     path('upload/', file_upload_view, name='upload'),
     path('download/<path:s3_key>/', file_download_view, name='download'),
     path('delete/<path:s3_key>/', file_delete_view, name='delete'),
     path('rename/', file_rename_view, name='rename'),
     path('create_folder/', create_folder_view, name='create_folder'),

]