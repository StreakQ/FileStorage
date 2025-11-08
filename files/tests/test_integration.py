# tests/test_integration.py
from django.test import TestCase
from django.contrib.auth.models import User
from moto import mock_aws
import boto3


@mock_aws
class TestIntegrationServices(TestCase):
    def setUp(self):
        # Создаём S3-клиент для использования в тестах
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.s3_client.create_bucket(Bucket='user-files')

        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client.login(username='testuser', password='password123')

    def test_file_manager_requires_login(self):
        self.client.logout()
        response = self.client.get('/files/manager/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login', response.url)

    def test_create_folder_view_creates_folder(self):
        data = {
            'folder_name': 'test-folder',
            'current_path': 'user-1-files/'
        }
        response = self.client.post('/files/create_folder/', data)
        self.assertRedirects(response, '/files/manager/?path=user-1-files/')

        # Проверяем, что объект-папка создан
        response = self.s3_client.list_objects_v2(
            Bucket='user-files',
            Prefix='user-1-files/test-folder/',
            Delimiter='/'
        )
        contents = response.get('Contents', [])
        self.assertTrue(
            any(obj['Key'] == 'user-1-files/test-folder/' for obj in contents),
            "Папка не была создана в S3"
        )