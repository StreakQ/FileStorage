from botocore.exceptions import ClientError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
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
        self.s3_client.put_object(
            Bucket='user-files',
            Key='user-1-files/docs/report.pdf',
            Body=b'Hello World!'
        )

        data = {
            's3_key': 'user-1-files/docs/report.pdf',
            'new_name': 'new_name.pdf'
        }

        response = self.client.post('/files/rename/', data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'files/file_manager.html')

        new_obj = self.s3_client.get_object(
            Bucket='user-files',
            Key='user-1-files/docs/new_name.pdf'
        )
        self.assertEqual(new_obj['Body'].read(), b'Hello World!')

        with self.assertRaises(ClientError):
            self.s3_client.get_object(Bucket='user-files', Key='user-1-files/docs/report.pdf')

    def test_rename_folder_success(self):
        self.s3_client.put_object(Bucket='user-files', Key='user-1-files/docs/', Body=b'')
        self.s3_client.put_object(Bucket='user-files', Key='user-1-files/docs/report.pdf', Body=b'content')

        data = {
            's3_key': 'user-1-files/docs/',
            'new_name': 'new_docs'
        }

        response = self.client.post('/files/rename/', data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'files/file_manager.html')

        self.s3_client.get_object(Bucket='user-files', Key='user-1-files/new_docs/')
        self.s3_client.get_object(Bucket='user-files', Key='user-1-files/new_docs/report.pdf')

        with self.assertRaises(ClientError):
            self.s3_client.get_object(Bucket='user-files', Key='user-1-files/docs/')
        with self.assertRaises(ClientError):
            self.s3_client.get_object(Bucket='user-files', Key='user-1-files/docs/report.pdf')

    def test_rename_other_user_files_returns_404(self):
        self.s3_client.put_object(Bucket='user-files', Key='user-2-files/docs/report.pdf', Body=b'content')

        data = {
            's3_key': 'user-2-files/docs/',
            'new_name': 'new_docs'
        }
        response = self.client.post('/files/rename/', data, follow=True)
        self.assertEqual(response.status_code, 404)

    @patch('files.services.file_storage_service.FileStorageService.rename_object')
    def test_rename_object_fails_but_returns_redirect(self, mock_rename_object):
        mock_rename_object.return_value = False
        self.s3_client.put_object(Bucket='user-files', Key='user-1-files/docs/report.pdf', Body=b'content')

        data = {
            's3_key': 'user-1-files/docs/',
            'new_name': 'new_docs'
        }
        response = self.client.post('/files/rename/', data, follow=True)
        self.assertTemplateUsed(response, 'files/file_manager.html')

    def test_rename_object_view_get_request_redirects(self):
        response = self.client.get('/files/rename/')
        self.assertRedirects(response, '/files/manager/')

    def test_delete_file_success(self):
        self.s3_client.put_object(Bucket='user-files',
                                  Key='user-1-files/docs/report.pdf',
                                  Body=b'Hello World!')

        url = reverse('files:delete', kwargs={'s3_key': 'user-1-files/docs/report.pdf'})
        response = self.client.post(url, follow=True)

        self.assertTemplateUsed(response, 'files/file_manager.html')
        self.assertEqual(response.status_code, 200)

        with self.assertRaises(ClientError):
            self.s3_client.get_object(Bucket='user-files', Key='user-1-files/docs/report.pdf')

    def test_delete_folder_success(self):

        self.s3_client.put_object(Bucket='user-files',
                                  Key='user-1-files/docs/',
                                  Body=b'')

        self.s3_client.put_object(Bucket='user-files',
                                  Key='user-1-files/docs/report.pdf',
                                  Body=b'Hello World!')

        url = reverse('files:delete', kwargs={'s3_key': 'user-1-files/docs/'})
        response = self.client.post(url, follow=True)

        self.assertTemplateUsed(response, 'files/file_manager.html')

        with self.assertRaises(ClientError):
            self.s3_client.get_object(Bucket='user-files', Key='user-1-files/docs/report.pdf')
        with self.assertRaises(ClientError):
            self.s3_client.get_object(Bucket='user-files', Key='user-1-files/docs/')

    def test_delete_other_user_files_returns_404(self):

        self.s3_client.put_object(Bucket='user-files',
                                  Key='user-2-files/docs/report.pdf',
                                  Body=b'Hello World!')

        url = reverse('files:delete', kwargs={'s3_key': 'user-2-files/docs/report.pdf'})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_delete_view_get_request_redirects(self):
        response = self.client.get('/files/create_folder/')
        self.assertRedirects(response, '/files/manager/')

    def test_download_file_success(self):
        self.s3_client.put_object(Bucket='user-files',
                                  Key='user-1-files/docs/report.pdf',
                                  Body=b'Hello World!')
        url = reverse('files:download', kwargs={'s3_key': 'user-1-files/docs/report.pdf'})
        response = self.client.get(url)

        self.assertTrue(response.status_code, 200)

    def test_download_file_returns_404_on_invalid_prefix(self):
        self.s3_client.put_object(Bucket='user-files',
                                  Key='user-2-files/docs/report.pdf',
                                  Body=b'Hello World!')

        response = self.client.get('/files/download/user-2-files/docs/report.pdf/')

        self.assertEqual(response.status_code, 404)

    def test_download_file_returns_404_on_nonexistent_file(self):
        self.s3_client.put_object(Bucket='user-files',
                                  Key='user-1-files/docs/report.pdf',
                                  Body=b'Hello World!')

        response = self.client.get('/files/download/user-1-files/docs/repo.pdf/')

        self.assertEqual(response.status_code, 404)

    def test_download_view_allows_only_get_requests(self):
        response = self.client.post('/files/download/user-1-files/docs/report.pdf/')
        self.assertEqual(response.status_code, 404)

    def test_download_view_sets_correct_headers(self):
        self.s3_client.put_object(Bucket='user-files',
                                  Key='user-1-files/docs/report.pdf',
                                  Body=b'Hello World!')

        url = reverse('files:download', kwargs={'s3_key': "user-1-files/docs/report.pdf"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=report.pdf')

    def test_upload_view_get_request_redirects(self):
        url = reverse('files:delete', kwargs={'s3_key': 'user-1-files/docs/report.pdf'})
        response = self.client.get(url)

        self.assertRedirects(response,'/files/manager/')

    def test_upload_files_success(self):
        file1 = SimpleUploadedFile('file1.txt', b'Hello World!', 'text/plain')
        file2 = SimpleUploadedFile('file2.txt', b'Hello World!', 'text/plain')

        data = {
            'files': [file1, file2],
            'current_path': 'user-1-files/docs/'
        }

        response = self.client.post('/files/upload/', data)
        self.assertRedirects(response, '/files/manager/?path=user-1-files/docs/')

        obj1 = self.s3_client.get_object(Bucket='user-files', Key='user-1-files/docs/file1.txt')
        obj2 = self.s3_client.get_object(Bucket='user-files', Key='user-1-files/docs/file2.txt')
        self.assertEqual(obj1['Body'].read(), b'Hello World!')
        self.assertEqual(obj2['Body'].read(), b'Hello World!')

    def test_upload_file_view_get_request_redirects(self):
        response = self.client.get('/files/upload/')
        self.assertRedirects(response, '/files/manager/')

    @patch('files.services.file_storage_service.FileStorageService.upload_file')
    def test_upload_file_make_correct_filename_in_s3(self, mock_upload):
        mock_upload.return_value = True

        file = SimpleUploadedFile('file1.txt', b'Hello World!', 'text/plain')
        data = {'files': [file], 'current_path': 'user-1-files/docs/'}

        response = self.client.post('/files/upload/', data, format='multipart')

        mock_upload.assert_called_once()
        call_kwargs = mock_upload.call_args[1]
        self.assertEqual(call_kwargs['filename_in_s3'], 'user-1-files/docs/file1.txt')

    def test_file_manager_requires_login(self):
        self.client.logout()
        response = self.client.get('/files/manager/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login', response.url)
