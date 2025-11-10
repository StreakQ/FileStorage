from django.test import TestCase
from django.contrib.auth.models import User
from moto import mock_aws
import boto3
from unittest.mock import patch


@mock_aws
class TestIntegrationServices(TestCase):
    def setUp(self):
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.s3_client.create_bucket(Bucket='user-files')

        self.user = User.objects.create_user(
            id=1,
            username='testuser',
            password='password123'
        )
        self.client.login(username='testuser', password='password123')

    def test_create_folder_view_creates_folder_success(self):

        data = {
            'folder_name': 'create_folder',
            'current_path': 'user-1-files/'
        }

        response = self.client.post('/files/create_folder/', data)

        self.assertRedirects(response, '/files/manager/?path=user-1-files%2Fcreate_folder%2F')

    def test_create_folder_view_creates_folder_with_empty_folder_name(self):
        data = {
            'folder_name': '',
            'current_path': 'user-1-files/'
        }
        response = self.client.post('/files/create_folder/', data)
        self.assertRedirects(response, '/files/manager/?path=user-1-files/')

    def test_create_folder_view_creates_folder_in_foreign_folder_returns_404(self):
        data = {
            'folder_name': 'create_folder',
            'current_path': 'user-2-files/'
        }

        response = self.client.post('/files/create_folder/', data)

        self.assertEqual(response.status_code, 404)

    def test_create_folder_view_get_request_redirects(self):
        """GET - запрос на /create_folder/ должен перенаправлять"""
        response = self.client.get('/files/create_folder/')
        self.assertRedirects(response, '/files/manager/')

    def test_rename_file_success(self):
        pass

    def test_rename_folder_success(self):
        pass

    def test_rename_with_empty_new_name_does_nothing(self):
        pass

    def test_rename_other_user_files_returns_404(self):
        pass

    @patch('files.services.file_storage_service.FileStorageService.rename_object')
    def test_rename_object_fails_but_returns_redirect(self, mock_rename_object):
        pass

    def test_rename_object_view_get_request_redirects(self):
        pass

    def test_file_manager_requires_login(self):
        self.client.logout()
        response = self.client.get('/files/manager/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login', response.url)