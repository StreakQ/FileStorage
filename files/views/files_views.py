from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.http import Http404
from django.contrib.auth.decorators import login_required
from files.services.fileStorage_service import FileStorageService
import logging
from urllib.parse import unquote
from typing import List, Dict

logger = logging.getLogger(__name__)


@csrf_protect
@login_required
def file_manager_view(request):
    """
    Отображает файловый менеджер
    :param request:
    :return:
    """
    try:
        user = request.user

        encoded_path = request.GET.get('path', '')
        current_path = unquote(encoded_path) if encoded_path else ''

        logger.debug(f"Текущий путь (переданный в ?path=): {current_path}")

        storage_service = FileStorageService()

        items = storage_service.list_files(user_id=user.id, prefix=current_path)
        logger.debug(f"Получено {len(items)} для отображения")

        breadcrumbs = _build_breadcrumbs(current_path)
        logger.debug(f"Breadcrumbs: {breadcrumbs}")

        context = {
            'breadcrumbs': breadcrumbs,
            'items': items,
            "current_path": current_path,
        }

        return render(request, "files/file_manager.html", context)

    except Exception as e:
        logger.error(f"Ошибка в file_manager_view для пользователя {request.user.id}: {e}", exc_info=True)
        return render(request, 'files/error.html', {'error_message': 'Произошла ошибка при загрузке файлов.'})


def _build_breadcrumbs(path: str) -> List[Dict]:
    """
    Вспомогательная функция для построения навигационной цепочки из пути.

    :param path: Относительный путь

    :return: list[dict] - Список из словарей, содержащий: {'name': "...", 'url_path': "..."}
    """
    if not path:
        return []

    parts = path.rstrip('/').split('/')
    breadcrumbs = []
    accumulated_path = ""
    for part in parts:
        if not part:
            continue

        if accumulated_path:
            accumulated_path += f"{part}/"
        else:
            accumulated_path = f"{part}/"

        breadcrumbs.append({
            'name': part,
            'url_path': accumulated_path
        })

    return breadcrumbs

