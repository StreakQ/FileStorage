import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import logging
from typing import Union, BinaryIO, List, Dict, Any
from .storage_strategy import StorageStrategy

logger = logging.getLogger(__name__)


class MinIOStorageStrategy(StorageStrategy):
    """
    Конкретная реализация стратегии хранения для MinIO (S3-совместимого хранилища).
    """

    def __init__(self):
        """
        Инициализирует клиент S3 для взаимодействия с MinIO.
        """
        session = boto3.session.Session()
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        if not settings.TESTING:
            self.s3_client = session.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                region_name=settings.AWS_S3_REGION_NAME,
            )
        else:
            self.s3_client = session.client('s3', region_name='us-east-1')

        if not settings.TESTING:
            self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """
        Проверяет наличие бакета и создает его при необходимости.

        Raises:
            botocore.exceptions.ClientError: Если возникает ошибка, отличная от 404.
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Бакет {self.bucket_name} существует")

        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                logger.info(f"Бакет {self.bucket_name} не существует, создаю...")
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Бакет {self.bucket_name} создан")
            else:
                logger.error(f"Ошибка при проверке бакета {self.bucket_name}: {e}")
                raise e

    def upload_file(self, user_id: int, file_obj: Union[BinaryIO, bytes], filename_in_s3: str) -> bool:
        """
        Загружает файл в бакет MinIO.

        Args:
            user_id (int): Идентификатор пользователя Django.
            file_obj (Union[BinaryIO, bytes]): Объект файла для загрузки.
            filename_in_s3 (str): Имя файла и путь внутри папки пользователя, под которым он будет сохранен.

        Returns:
            bool: True, если загрузка прошла успешно, иначе False.

        Raises:
            ValueError: Если имя файла пустое.
        """
        if not filename_in_s3 or not filename_in_s3.strip():
            logger.error("Имя файла не может быть пустым")
            raise ValueError("Имя файла не может быть пустым")

        expected_prefix = f"user-{user_id}-files/"
        if not filename_in_s3.startswith(expected_prefix):
            logger.error(f"Попытка загрузки вне зоны доступа: {filename_in_s3}")
            return False

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Body=file_obj,
                Key=filename_in_s3,
            )
            logger.info(f'Файл успешно загружен в {self.bucket_name}/{filename_in_s3}')
            return True

        except ClientError as e:
            logger.error(f"Ошибка загрузки файла {filename_in_s3} для пользователя {user_id}: {e}")
            return False

    def list_files(self, user_id: int, prefix: str = '') -> List[Dict[str, Any]]:
        """
        Получает список файлов и папок из MinIO.

        Args:
            user_id (int): Идентификатор пользователя Django.
            prefix (str): Префикс пути для поиска файлов (например, 'user-1-files/www/').

        Returns:
            List[Dict[str, Any]]: Список словарей с информацией о файлах/папках.
        """
        s3_prefix = prefix.rstrip('/') + '/' if prefix else f"user-{user_id}-files/"

        expected_prefix = f"user-{user_id}-files/"
        if not s3_prefix.startswith(expected_prefix):
            logger.warning(f"Запрещённый префикс: {s3_prefix}")
            return []

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=s3_prefix,
                Delimiter='/'
            )

            items = []

            # Папки
            for cp in response.get('CommonPrefixes', []):
                folder_prefix = cp['Prefix']
                folder_name = folder_prefix[len(s3_prefix):].rstrip('/')
                if folder_name:
                    items.append({
                        'type': 'folder',
                        'name': folder_name,
                        'full_key': folder_prefix
                    })

            # Файлы
            for item in response.get('Contents', []):
                key = item['Key']
                if key == s3_prefix:
                    continue
                file_name = key[len(s3_prefix):]
                if file_name:
                    items.append({
                        'type': 'file',
                        'name': file_name,
                        'full_key': key,
                        'size': item['Size'],
                        'last_modified': item['LastModified']
                    })

            logger.debug(f"[list_files] Найдено {len(items)} элементов по префиксу '{s3_prefix}'")
            return items

        except ClientError as e:
            logger.error(f"[list_files] Ошибка S3: {e}")
            return []

    def delete_object(self, user_id: int, s3_key: str) -> bool:
        """
        Удаляет файл или папку (рекурсивно, все объекты с префиксом) из MinIO.

        Args:
            user_id (int): Идентификатор пользователя Django.
            s3_key (str): Относительный путь к файлу или папке.

        Returns:
            bool: True, если удаление прошло успешно, иначе False.
        """
        if not s3_key or not s3_key.strip():
            logger.error("Нельзя удалить объект с пустым ключом")
            return False

        full_s3_key = s3_key

        try:
            if full_s3_key.endswith('/'):
                # Удаление папки
                prefix_to_delete = full_s3_key
                logger.info(f"Начало удаления папки с префиксом {prefix_to_delete}")

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
        Переименовывает файл или папку в MinIO (копирование и удаление).

        Args:
            user_id (int): Идентификатор пользователя Django.
            s3_key (str): Относительный путь к файлу или папке (например, 'folder/old_name.txt').
            new_name (str): Новое имя (только имя, не путь!).

        Returns:
            bool: True, если переименование прошло успешно, иначе False.
        """
        print(f"[rename] Получен s3_key: '{s3_key}'")

        if not new_name:
            logger.error(f"Новое имя не может быть пустым")
            return False

        old_full_key = s3_key
        is_folder = old_full_key.endswith('/')

        operations_count = 0
        print(f"[rename] Обрабатываем {'папку' if is_folder else 'файл'}: {old_full_key}, is_folder={is_folder}")

        try:
            if is_folder:
                old_prefix = s3_key
                print(f"[rename] Используем Prefix для list_objects_v2: '{old_prefix}'")
                parent_prefix_parts = old_prefix.rstrip('/').split('/')[:-1]
                parent_prefix = '/'.join(parent_prefix_parts)
                if parent_prefix:
                    parent_prefix += '/'
                new_prefix = f"{parent_prefix}{new_name}/"

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
                                Bucket=self.bucket_name,
                                CopySource=copy_source,
                                Key=new_object_key
                            )
                            self.s3_client.delete_object(Bucket=self.bucket_name, Key=old_object_key)
                            operations_count += 1

                print(f"Папка {old_prefix} переименована в {new_prefix}, обработано {operations_count} объектов")

            else:
                old_key = old_full_key
                parent_prefix_parts = old_key.split('/')[:-1]
                parent_prefix = '/'.join(parent_prefix_parts)
                if parent_prefix:
                    parent_prefix += '/'
                new_key = f"{parent_prefix}{new_name}"

                copy_source = {"Bucket": self.bucket_name, "Key": old_key}
                self.s3_client.copy_object(
                    Bucket=self.bucket_name,
                    Key=new_key,
                    CopySource=copy_source
                )
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=old_key)
                print(f"Файл {old_key} переименован в {new_key}")

            return True

        except ClientError as e:
            print(f"Ошибка при переименовании объекта '{old_full_key}': {e}")
            return False
        except Exception as e:
            print(f"Неожиданная ошибка при переименовании объекта '{old_full_key}': {e}")
            return False

    def create_folder(self, user_id: int, folder_s3_key: str) -> bool:
        """
        Создаёт папку в MinIO по полному S3-ключу.

        Args:
            user_id (int): ID пользователя (для проверки доступа).
            folder_s3_key (str): Полный ключ папки (должен начинаться с user-{id}-files/).

        Returns:
            bool: True при успехе.
        """
        expected_prefix = f"user-{user_id}-files/"

        if not folder_s3_key.startswith(expected_prefix):
            logger.error(f"Отказ в создании папки: путь '{folder_s3_key}' вне зоны доступа пользователя {user_id}")
            return False

        if not folder_s3_key.endswith('/'):
            folder_s3_key += '/'

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=folder_s3_key,
                Body=b''
            )
            logger.info(f"Папка создана: {folder_s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Ошибка S3 при создании папки {folder_s3_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при создании папки {folder_s3_key}: {e}", exc_info=True)
            return False
