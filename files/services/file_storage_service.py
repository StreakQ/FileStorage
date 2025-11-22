from files.services.storage.storage_strategy import StorageStrategy
from typing import Union, BinaryIO, List, Dict, Any


class FileStorageService:
    """
    Сервис для работы с файлами, использующий стратегию хранения.
    """

    def __init__(self, storage_strategy: StorageStrategy):
        """
        Инициализирует сервис с конкретной стратегией хранения.

        Args:
            storage_strategy (StorageStrategy): Стратегия хранения файлов (например, MinIO).
        """
        self.strategy = storage_strategy

    def upload_file(self, user_id: int, file_obj: Union[BinaryIO, bytes], filename_in_s3: str) -> bool:
        """
        Загружает файл в хранилище через стратегию.

        Args:
            user_id (int): Идентификатор пользователя Django.
            file_obj (Union[BinaryIO, bytes]): Объект файла для загрузки.
            filename_in_s3 (str): Имя файла и путь внутри папки пользователя.

        Returns:
            bool: True, если загрузка прошла успешно, иначе False.
        """
        return self.strategy.upload_file(user_id, file_obj, filename_in_s3)

    def list_files(self, user_id: int, prefix: str = '') -> List[Dict[str, Any]]:
        """
        Получает список файлов и папок через стратегию.

        Args:
            user_id (int): Идентификатор пользователя Django.
            prefix (str): Префикс пути для поиска файлов.

        Returns:
            List[Dict[str, Any]]: Список файлов/папок.
        """
        return self.strategy.list_files(user_id, prefix)

    def delete_object(self, user_id: int, s3_key: str) -> bool:
        """
        Удаляет файл или папку через стратегию.

        Args:
            user_id (int): Идентификатор пользователя Django.
            s3_key (str): Относительный путь к файлу или папке.

        Returns:
            bool: True, если удаление прошло успешно, иначе False.
        """
        return self.strategy.delete_object(user_id, s3_key)

    def rename_object(self, user_id: int, s3_key: str, new_name: str) -> bool:
        """
        Переименовывает файл или папку через стратегию.

        Args:
            user_id (int): Идентификатор пользователя Django.
            s3_key (str): Относительный путь к файлу или папке.
            new_name (str): Новое имя.

        Returns:
            bool: True, если переименование прошло успешно, иначе False.
        """
        return self.strategy.rename_object(user_id, s3_key, new_name)

    def create_folder(self, user_id: int, folder_s3_key: str) -> bool:
        """
        Создаёт папку через стратегию.

        Args:
            user_id (int): ID пользователя.
            folder_s3_key (str): Полный ключ папки.

        Returns:
            bool: True при успехе.
        """
        return self.strategy.create_folder(user_id, folder_s3_key)

    def ensure_bucket_exists(self):
        """
        Проверяет/создаёт бакет через стратегию.
        """
        self.strategy._ensure_bucket_exists()
