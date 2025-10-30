from django.urls import path
from .views.files_views import *

app_name = 'files'

urlpatterns = [
     path('manager/', file_manager_view, name='file_manager'),
     path('upload/', file_upload_view, name='upload'),
     path('download/<path:s3_key>/', file_download_view, name='download'),
     path('delete/<path:s3_key>/', file_delete_view, name='delete'),
     path('rename/<path:s3_key>/', file_rename_view, name='rename'),

]