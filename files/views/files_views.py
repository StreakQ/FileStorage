from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.http import Http404, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from files.services.file_storage_service import FileStorageService
from django.conf import settings
from django.contrib import messages
import logging
from urllib.parse import unquote, urlencode
from typing import List, Dict

logger = logging.getLogger(__name__)


bucket_name = settings.AWS_STORAGE_BUCKET_NAME


@login_required
def home_redirect_view(request):
    user_id = request.user.id
    user_folder = f"user-{user_id}-files/"

    from django.urls import reverse
    from urllib.parse import urlencode

    url = reverse('file_manager')
    query = urlencode({'path': user_folder})

    return redirect(f"{url}?{query}")


@csrf_protect
@login_required
def file_manager_view(request):
    service = FileStorageService()
    try:
        user = request.user
        user_id = user.id
        base_prefix = f"user-{user_id}-files/"

        encoded_path = request.GET.get('path', '')
        current_path = unquote(encoded_path) if encoded_path else ''

        logger.debug(f"[file_manager] Получен path: '{current_path}'")

        if not current_path or current_path == '/' or current_path.startswith('/'):
            current_path = base_prefix

        if not current_path.startswith(base_prefix):
            logger.warning(f"Подмена пути: {current_path} → принудительно установлен {base_prefix}")
            current_path = base_prefix


        if not current_path.endswith('/'):
            current_path += '/'

        items = service.list_files(user_id=user_id, prefix=current_path)
        breadcrumbs = _build_breadcrumbs(current_path)

        context = {
            'items': items,
            'breadcrumbs': breadcrumbs,
            'current_path': current_path,
        }

        return render(request, "files/file_manager.html", context)

    except Exception as e:
        logger.error(f"Ошибка в file_manager_view: {e}", exc_info=True)
        return render(request, 'files/error.html', {'error_message': 'Ошибка загрузки'})


@login_required
@csrf_protect
def file_upload_view(request):
    service = FileStorageService()

    if request.method == 'POST':
        user_id = request.user.id
        files = request.FILES.getlist('files')
        current_path = request.POST.get('current_path', '').strip()

        logger.debug(f"[upload] Получен current_path: '{current_path}'")

        if not current_path or not current_path.startswith(f"user-{user_id}-files"):
            current_path = f"user-{user_id}-files/"

        for uploaded_file in files:
            filename_in_s3 = f"{current_path}{uploaded_file.name}"

            success = service.upload_file(
                user_id=user_id,
                file_obj=uploaded_file,
                filename_in_s3=filename_in_s3
            )
            if not success:
                messages.error(request, f"Ошибка при загрузке {uploaded_file.name}")

        return redirect_with_path(current_path)

    return redirect('files:file_manager')


@login_required
@csrf_protect
def file_download_view(request, s3_key):
    service = FileStorageService()
    """
    Позволяет пользователю скачать файлы из облака
    :param s3_key:
    :param request:
    """

    user_id = request.user.id
    expected_prefix = f"user-{user_id}-files/"

    if not s3_key.startswith(expected_prefix):
        raise Http404("Файл не найден или доступ запрещен")

    try:
        response = service.s3_client.get_object(Bucket=bucket_name, Key=s3_key)

        file_stream = response["Body"]
        content_type = response.get("ContentType", 'application/octet-stream')
        content_length = response.get("ContentLength", None)

        file_name = s3_key.split("/")[-1]

        http_response = StreamingHttpResponse(file_stream, content_type=content_type)

        http_response["Content-Disposition"] = f"attachment; filename={file_name}"

        if content_length:
            http_response["Content-Length"] = str(content_length)

        logger.info(f"Файл {s3_key} начал скачиваться")
        return http_response

    except service.s3_client.exceptions.NoSuchKey:
        logger.error(f"Файл не найден в S3: {s3_key}")
        raise Http404("Файл не найден")

    except Exception as e:
        logger.error(f"Ошибка при скачивании файла {s3_key}: {e}", exc_info=True)
        return redirect('files:file_manager')


@login_required
@csrf_protect
def file_delete_view(request, s3_key):
    service = FileStorageService()
    """
    Позволяет пользователю удалить файл
    :param s3_key:
    :param request:
    :return:
    """
    if request.method == "POST":
        user_id = request.user.id
        expected_prefix = f"user-{user_id}-files/"

        if not s3_key.startswith(expected_prefix):
            raise Http404("Файл не найден или доступ запрещен")

        try:

            success = service.delete_object(
                user_id=user_id,
                s3_key=s3_key,
            )
            if success:
                logger.info(f"файл {s3_key} удален")

        except Exception as e:
            logger.error(f"Ошибка при удалении файла {s3_key}: {e}", exc_info=True)

        return redirect('files:file_manager')
    else:
        return redirect('files:file_manager')


@login_required
@csrf_protect
def file_rename_view(request):
    service = FileStorageService()

    if request.method == "POST":
        user_id = request.user.id
        expected_prefix = f"user-{user_id}-files/"

        # Получаем данные из формы
        s3_key = request.POST.get('s3_key', '').strip()
        new_name = request.POST.get('new_name', '').strip()

        # Проверки
        if not new_name:
            return redirect('files:file_manager')

        if not s3_key:
            return redirect('files:file_manager')

        # Защита: только внутри своей папки
        if not s3_key.startswith(expected_prefix):
            logger.warning(f"Попытка доступа к чужому файлу: {s3_key} (пользователь {user_id})")
            return redirect('files:file_manager')

        try:
            success = service.rename_object(
                user_id=user_id,
                s3_key=s3_key,
                new_name=new_name
            )
            if success:
                messages.success(request, f'Объект "{new_name}" успешно переименован.')
            else:
                messages.error(request, 'Не удалось переименовать объект.')

        except Exception as e:
            logger.error(f"Ошибка при переименовании {s3_key}: {e}", exc_info=True)
            messages.error(request, 'Произошла ошибка на сервере.')

        return redirect_with_path(s3_key.rsplit('/', 1)[0] + '/')  # редирект в родительскую папку

    return redirect('files:file_manager')


@login_required
@csrf_protect
def create_folder_view(request):
    service = FileStorageService()
    if request.method == "POST":
        user_id = request.user.id
        folder_name = request.POST.get('folder_name', '').strip()
        current_path = request.POST.get('current_path', '').strip()

        logger.debug(f"[create_folder] current_path='{current_path}', folder_name='{folder_name}'")

        if not folder_name:
            messages.error(request, 'Имя папки не может быть пустым')
            return redirect_with_path(current_path or f"user-{user_id}-files/")

        if not current_path.startswith(f"user-{user_id}-files"):
            raise Http404("Доступ запрещен")

        if not current_path.endswith('/'):
            current_path += '/'
        full_path = f"{current_path}{folder_name}/"

        try:
            success = service.create_folder(user_id=user_id, folder_s3_key=full_path)
            if success:
                messages.success(request, f'Папка "{folder_name}" создана')
                return redirect_with_path(full_path)
            else:
                messages.error(request, 'Не удалось создать папку')
                return redirect_with_path(current_path)
        except Exception as e:
            logger.error(f"Ошибка при создании папки {full_path}: {e}", exc_info=True)
            messages.error(request, 'Ошибка сервера')
            return redirect_with_path(current_path)

    return redirect('files:file_manager')


def redirect_with_path(path: str):
    from django.urls import reverse
    from urllib.parse import quote
    query = f"?path={quote(path)}" if path else ""
    return redirect(f"{reverse('files:file_manager')}{query}")


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
