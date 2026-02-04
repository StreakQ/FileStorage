from abc import ABC, abstractmethod
from typing import Union, BinaryIO, List, Dict, Any


class StorageStrategy(ABC):
    """
    Абстрактный класс, определяющий общий интерфейс для всех стратегий хранения файлов.
    """

    @abstractmethod
    def upload_file(self, user_id: int, file_obj: Union[BinaryIO, bytes], filename_in_s3: str) -> bool:
        """
        Загружает файл в хранилище.

        Args:
            user_id (int): Идентификатор пользователя Django.
            file_obj (Union[BinaryIO, bytes]): Объект файла для загрузки.
            filename_in_s3 (str): Имя файла и путь внутри папки пользователя, под которым он будет сохранен.

        Returns:
            bool: True, если загрузка прошла успешно, иначе False.
        """
        pass

    @abstractmethod
    def get_object(self, user_id: int, filename_in_s3: str) -> dict:
        """
        Получает объект из хранилища.
        Args:
            user_id: Идентификатор пользователя.
            filename_in_s3:Имя файла и путь внутри папки пользователя

        Returns:
            dict с метаданными:

        """
        pass

    @abstractmethod
    def list_files(self, user_id: int, prefix: str = '') -> List[Dict[str, Any]]:
        """
        Получает список файлов и папок.

        Args:
            user_id (int): Идентификатор пользователя Django.
            prefix (str): Префикс пути для поиска файлов (например, 'user-1-files/www/').

        Returns:
            List[Dict[str, Any]]: Список словарей с информацией о файлах/папках.
        """
        pass

    @abstractmethod
    def delete_object(self, user_id: int, s3_key: str) -> bool:
        """
        Удаляет файл или папку (рекурсивно, все объекты с префиксом).

        Args:
            user_id (int): Идентификатор пользователя Django.
            s3_key (str): Относительный путь к файлу или папке.

        Returns:
            bool: True, если удаление прошло успешно, иначе False.
        """
        pass

    @abstractmethod
    def rename_object(self, user_id: int, s3_key: str, new_name: str) -> bool:
        """
        Переименовывает файл или папку.

        Args:
            user_id (int): Идентификатор пользователя Django.
            s3_key (str): Относительный путь к файлу или папке.
            new_name (str): Новое имя (только имя, не путь!).

        Returns:
            bool: True, если переименование прошло успешно, иначе False.
        """
        pass

    @abstractmethod
    def create_folder(self, user_id: int, folder_s3_key: str) -> bool:
        """
        Создаёт папку по полному S3-ключу.

        Args:
            user_id (int): ID пользователя (для проверки доступа).
            folder_s3_key (str): Полный ключ папки (должен начинаться с user-{id}-files/).

        Returns:
            bool: True при успехе.
        """
        pass

    @abstractmethod
    def _ensure_bucket_exists(self) -> None:
        """
        Проверяет наличие бакета и создает его при необходимости.
        """
        pass