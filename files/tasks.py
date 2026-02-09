from celery import shared_task
import time
import logging
from files.services.file_storage_service import FileStorageService
from files.services.strategy_factory import get_storage_strategy
from django.http import FileResponse
from django.core.files.base import ContentFile
from io import BytesIO

logger = logging.getLogger(__name__)


@shared_task
def generate_download_url_task(user_id: int, filename_in_s3: str) -> str:
    """
    Асинхронная задача для генерации подписанного URL.

    Args:
        user_id: Идентификатор пользователя.
        filename_in_s3: Путь внутри папки пользователя для файла, с которым будут выполнятся операции.

    Returns: Подписанный URL.

    """
    logger.info(f"Генерация подписанного URL для пользователя: {user_id} по пути: {filename_in_s3}")

    try:
        storage_strategy = get_storage_strategy()

        url = storage_strategy.generate_download_url(
            user_id=user_id,
            filename_in_s3=filename_in_s3
        )

        if url:
            logger.info(f"Сгенерирован подписанный URL для пользователя: {user_id} по пути: {filename_in_s3}")

    except Exception as e:
        logger.error(f"Ошибка при генерации подписанного URL для пользователя: {user_id} по пути: {filename_in_s3}")
        raise e