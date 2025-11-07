import unittest
from unittest.mock import patch

from botocore.exceptions import ClientError
from django.test import TestCase
from django.contrib.auth.models import User
from files.services.fileStorage_service import FileStorageService


class FileStorageServiceTest(TestCase):
    def setUp(self):
        self.service = FileStorageService()

    def test_upload_file_raises_error_on_empty_filename(self):
        """Если имя файла пустое, выбрасывается ValueError"""
        with self.assertRaises(ValueError):
            self.service.upload_file(user_id=1,
                                     file_obj=b'test_file',
                                     filename_in_s3='')

    def test_upload_file_builds_correct_s3_keys(self):
        """Проверяет, что при загрузке, s3_key формируется правильно"""
        file_data = b'test_file'

        with patch.object(self.service.s3_client, 'put_object') as mock_put:
            result = self.service.upload_file(user_id=1,
                                              file_obj=file_data,
                                              filename_in_s3='/docs/report.pdf')

            mock_put.assert_called_once()
            call_kwargs = mock_put.call_args[1]
            self.assertEqual(call_kwargs['Key'], 'user-1-files/docs/report.pdf')
            self.assertTrue(result)

    def test_upload_file_returns_true_on_success(self):
        """Если put_object прошел успешно - возвращает True"""
        file_data = b'test_file'

        with patch.object(self.service.s3_client, 'put_object'):
            result = self.service.upload_file(user_id=1,
                                              file_obj=file_data,
                                              filename_in_s3='test.pdf')

            self.assertTrue(result)

    def test_upload_file_returns_false_on_client_error(self):
        """Если S3 вернул ошибку - возвращается False, а не исключение"""
        file_data = b'broken'
        with patch.object(self.service.s3_client, 'put_object') as mock_put:
            mock_put.side_effect = ClientError(
                {'Error': {'Code': 'ClientError'}},
                'put_object')

            result = self.service.upload_file(user_id=1,
                                              file_obj=file_data,
                                              filename_in_s3='bad.pdf')
            self.assertFalse(result)

    def test_delete_file_returns_true_on_success(self):
        """"""
        with patch.object(self.service.s3_client, 'delete_object'):
            result = self.service.delete_object(
                user_id=1,
                s3_key='user-1-files/docs/report.pdf')
            self.assertTrue(result)

    def test_delete_folder_with_objects_returns_true(self):
        pages = [
            {
                'Contents': [
                    {'Key': 'user-1-files/docs/file1.txt'},
                    {'Key': 'user-1-files/docs/file2.txt'}
                ]
            }
        ]

        with patch.object(self.service.s3_client, 'get_paginator') as mock_paginator:
            mock_paginator.return_value.paginate.return_value = pages

            with patch.object(self.service.s3_client, 'delete_objects') as mock_delete_objects:
                result = self.service.delete_object(
                    user_id=1,
                    s3_key='user-1-files/docs/'
                )

                self.assertTrue(result)
                mock_delete_objects.assert_called_once()

    def test_delete_empty_folder_returns_true(self):
        """"""
        with patch.object(self.service.s3_client, 'get_paginator') as mock_paginator:
            pages = [{"Contents": []}]
            mock_paginator.return_value.paginate.return_value = pages

            with patch.object(self.service.s3_client, 'delete_object') as mock_delete:
                result = self.service.delete_object(
                    user_id=1,
                    s3_key='user-1-files/docs/')

                self.assertTrue(result)
                mock_delete.assert_not_called()

    def test_delete_object_returns_false_on_client_error(self):
        """"""
        with patch.object(self.service.s3_client, 'delete_object') as mock_delete:
            mock_delete.side_effect = ClientError(
                {'Error': {'Code': 'ClientError'}},
                'delete_object')

            result = self.service.delete_object(
                user_id=1,
                s3_key='user-1-files/doc')

            self.assertFalse(result)

    def test_delete_object_with_empty_s3_key_returns_false(self):
        """"""
        with patch.object(self.service.s3_client, 'delete_object'):
            result = self.service.delete_object(
                user_id=1,
                s3_key='')
            self.assertFalse(result)

    def test_rename_file_returns_true_on_success(self):
        old_key = "user-1-files/docs/old.txt"
        new_name = "new.txt"

        with (
            patch.object(self.service.s3_client, 'copy_object') as mock_copy,
            patch.object(self.service.s3_client, 'delete_object') as mock_delete
        ):
            result = self.service.rename_object(
                user_id=1,
                s3_key=old_key,
                new_name=new_name
            )

            self.assertTrue(result)
            mock_copy.assert_called_once()
            mock_delete.assert_called_once()

    def test_rename_object_returns_false_on_client_error(self):
        with patch.object(self.service.s3_client, 'rename_object') as mock_rename:
            mock_rename.side_effect = ClientError(
                {'Error': {'Code': 'ClientError'}},
                'rename_object')

            result = self.service.rename_object(
                user_id=1,
                s3_key='folder/doc.pdf',
                new_name='new_name.pdf')

            self.assertFalse(result)

    def test_rename_folder_with_objects_returns_true(self):
        old_key = "user-1-files/docs/"
        new_name = "backup"

        pages = [{
            "Contents": [
                {"Key": "user-1-files/docs/file1.txt"},
                {"Key": "user-1-files/docs/sub/file2.txt"}
            ]}]

        with (
            patch.object(self.service.s3_client, 'get_paginator') as mock_paginator,
            patch.object(self.service.s3_client, 'copy_object') as mock_copy,
            patch.object(self.service.s3_client, 'delete_object') as mock_delete
        ):
            mock_paginator.return_value.paginate.return_value = pages

            result = self.service.rename_object(
                user_id=1,
                s3_key=old_key,
                new_name=new_name

            )
            self.assertTrue(result)

    def test_rename_object_with_empty_new_name_returns_false(self):
        with patch.object(self.service.s3_client, 'rename_object') as mock_rename:
            result = self.service.rename_object(user_id=1,
                                                s3_key='/folder/doc.pdf',
                                                new_name='')

            self.assertFalse(result)
            mock_rename.assert_not_called()

    def test_rename_file_correctly_builds_new_key(self):
        """Проверяет, что parent directory сохраняется"""
        old_key = "user-1-files/projects/report.pdf"
        new_name = "summary.pdf"

        with (
            patch.object(self.service.s3_client, 'copy_object') as mock_copy,
            patch.object(self.service.s3_client, 'delete_object') as mock_delete
        ):
            self.service.rename_object(
                user_id=1,
                s3_key=old_key,
                new_name=new_name
            )

            expected_key = "user-1-files/projects/summary.pdf"
            mock_copy.assert_called_once_with(
                Bucket='user-files',
                Key=expected_key,
                CopySource={'Bucket': 'user-files', 'Key': old_key}
            )

    def test_list_files(self):
        pass