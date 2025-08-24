import boto3
from django.conf import settings
from botocore.exceptions import ClientError
import logging
from typing import Union, BinaryIO

logger = logging.getLogger(__name__)


class FileStorageService:
    def __init__(self):
        """Инициализирует сервис хранения файлов"""
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """
        Проверяет наличие бакета и создает его при необходимости

        :raises
            botocore.exceptions.ClientError: Если возникает ошибка, отличная от 404
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logging.info(f"Бакет {self.bucket_name} существует")

        except ClientError as e:

            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                logging.info(f"Бакет {self.bucket_name} не существует")
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                logging.info(f"Бакет {self.bucket_name} создан")
            else:
                logging.error(f"Ошибка при проверке бакета {self.bucket_name}: {e}")
                raise e

    def upload_file(self, user_id: int, file_obj: Union[BinaryIO, bytes], filename_in_s3: str) -> bool:
        """
        Загружает файл в бакет.

        :param user_id: Идентификатор пользователя Django

        :param file_obj: Объект файла для загрузки.
            Это может быть объект из request.FILES или байтовая строка.

        :param filename_in_s3: Имя файла и путь внутри папки пользователя, под которым он будет сохранен.

        :return: True, если загрузка прошла успешно, иначе False.

        :raises
            ValueError: Если имя файла пустое
        """
        if not filename_in_s3:
            logger.error(f"Имя файла не может быть пустым")
            raise ValueError("Имя файла не может быть пустым")

        s3_key = f"user-{user_id}-files/{filename_in_s3.lstrip('/')}"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Body=file_obj,
                Key=s3_key,
            )
            logger.info(f'Файл успешно загружен в {self.bucket_name}/{s3_key}')
            return True

        except ClientError as e:
            logger.info(f"Ошибка загрузки файла {s3_key} для пользователя {user_id}: {e}")
            return False

    def list_files(self, user_id: int, prefix: str = '') -> list[dict]:
        """
        Получает Список файлов и папок для указанного пользователя и префикса.

        :param user_id:Идентификатор пользователя Django
        :param prefix: Префикс пути внутри пользователя

        :return:
            list[dict] - Список словарей, представляющий файлы или папки.
                Каждый словарь содержит ключи:
                - 'type': 'file' или 'folder'
                - 'name': имя файла или папки
                - 'full_key': Полный ключ s3
                - 'size': размер (только для файлов)
                - 'last_modified': время последнего изменения (только для файлов)
        """

        s3_prefix = f"user-{user_id}-files/{prefix.lstrip('/')}"
        if s3_prefix and not s3_prefix.endswith('/'):
            s3_prefix += '/'

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=s3_prefix,
                Delimiter='/'
            )
            items = []
            #Обработка папок
            for common_prefix in response.get('CommonPrefixes', []):
                folder_prefix = common_prefix.get('Prefix')
                folder_name = folder_prefix[len(s3_prefix):].rstrip('/')

                if folder_name:
                    items.append({
                        'type': 'folder',
                        'name': folder_name,
                        'full_key': folder_prefix
                    })

            #Обработка папок
            for item in response.get('Contents', []):
                key = item.get('Key')
                file_name = key[len(s3_prefix):]

                if file_name:
                    items.append({
                        'type': 'file',
                        'name': file_name,
                        'full_key': key,
                        'size': item.get('Size', 0),
                        'last_modified': item.get('LastModified', None)
                    })

            logger.debug(f"Получен список {len(items)} элементов для пользователя {user_id}")
            return items

        except ClientError as e:
            logger.error(f'Ошибка при получении списка элементов пользователя {user_id}: {e} ')
            return False

    def delete_object(self, user_id: int, s3_key: str) -> bool:
        """
        Удаляет файл или папку (рекурсивно, все объекты с префиксом)

        :param user_id: Идентификатор пользователя Django
        :param s3_key: Относительный путь к файлу или папке

        :return: True, если удаление прошло успешно, иначе False
        """
        full_s3_key = f"user-{user_id}-files/{s3_key}"

        try:
            if full_s3_key.endswith('/'):
                # Удаление папки
                prefix_to_delete = full_s3_key
                logger.info(f"Начало удаление папки с префиксом {full_s3_key}")

                paginator = self.s3_client.get_paginator('list_objects_v2')

                pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix_to_delete)

                delete_keys = []
                for page in pages:
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            delete_keys.append({"Key": obj['Key']})

                if delete_keys:
                    for i in range(0, len(delete_keys), 1000):
                        batch = delete_keys[i:i + 1000]
                        self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={'Objects': batch})

                    logger.info(f"Удалено {len(delete_keys)} объектов из папки {prefix_to_delete}")
                else:
                    logger.info(f"Папка {prefix_to_delete} пуста или не существует.")

            else:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=full_s3_key)

            return True

        except ClientError as e:
            logger.error(f"Ошибка при удалении объекта {full_s3_key} : {e}")
            return False

    def rename_object(self, user_id: int, s3_key: str, new_name: str) -> bool:
        """
        Переименовывает файл или папку.

        :param user_id: Идентификатор пользователя Django.
        :param s3_key: Относительный путь к файлу или папке (например, 'folder/old_name.txt').
        :param new_name: Новое имя (только имя, не путь!).

        :return: True, если переименование прошло успешно, иначе False.
        """
        if not new_name:
            logger.error(f"Новое имя не может быть пустым")
            return False

        old_full_key = f"user-{user_id}-files/{s3_key.lstrip('/')}"
        is_folder = old_full_key.endswith('/')

        operations_count = 0

        try:
            if is_folder:
                old_prefix = old_full_key
                parent_prefix_parts = old_prefix.rstrip('/').split('/')[:-1]
                parent_prefix = '/'.join(parent_prefix_parts)
                if parent_prefix:
                    parent_prefix += '/'
                new_prefix = f"{parent_prefix}{new_name}"

                paginator = self.s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=self.bucket_name, Prefix=old_prefix)

                for page in pages:
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            old_object_key = obj['Key']
                            relative_path = old_object_key[len(old_prefix):]
                            new_object_key = f"{new_prefix}{relative_path}"

                            copy_source = {"Bucket": self.bucket_name, "Key": old_object_key}
                            self.s3_client.copy_object(
                                CopySource=copy_source,
                                Bucket=self.bucket_name,
                                Key=new_object_key)

                            self.s3_client.delete_object(Bucket=self.bucket_name, Key=old_object_key)
                            operations_count += 1

                logger.info(f"Папка {old_prefix} переименована в {new_prefix}, обработано {operations_count} объектов")

            else:
                old_key = old_full_key
                parent_prefix_parts = old_key.split('/')[:-1]
                parent_prefix = '/'.join(parent_prefix_parts)

                if parent_prefix:
                    parent_prefix += '/'

                new_key = f"{parent_prefix}{new_name}"

                copy_source = {"Bucket": self.bucket_name, "Key": old_key}
                self.s3_client.copy_object(bucket_name=self.bucket_name, Key=new_key, CopySource=copy_source)
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=old_key)

                logger.info(f"Файл {old_key} переименован в {new_key}")

            return True

        except ClientError as e:
            logger.error(f"Ошибка при переименовании объекта '{old_full_key}': {e}")
            return False

        except Exception as e:
            logger.error(f"Неожиданная ошибка при переименовании объекта '{old_full_key}': {e}")
            return False

    def create_folder(self, user_id: int, folder_s3_key: str) -> bool:
        """
        Создает новую папку

        :param user_id: Идентификатор пользователя Django
        :param folder_s3_key: Желаемый префикс папки

        :return: True, если создание прошло успешно, иначе False
        """
        s3_key = f"user-{user_id}-files/{folder_s3_key.lstrip('/')}"
        if s3_key and not s3_key.endswith('/'):
            s3_key += '/'

        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=folder_s3_key, Body=b'')
            logger.info(f"Папка {s3_key} создана")
            return True

        except ClientError as e:
            logger.error(f"Ошибка при создании новой папки {s3_key} : {e}")
            return False

        except Exception as e:
            logger.error(f"Неожиданная ошибка при создании папки '{s3_key}': {e}")
            return False
