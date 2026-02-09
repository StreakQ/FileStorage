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
     path('download-async/<str:s3_key>/', initiate_file_download_async_view, name='initiate_download_async'),
     path('download-result/<str:task_id>/', get_download_url_result, name='get_download_url_result'),

]