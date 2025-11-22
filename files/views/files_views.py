from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.http import Http404, StreamingHttpResponse, HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required
from files.services.file_storage_service import FileStorageService
from files.services.storage.minio_strategy import MinIOStorageStrategy
from django.conf import settings
from django.contrib import messages
import logging
from urllib.parse import unquote, urlencode
from typing import List, Dict

logger = logging.getLogger(__name__)


bucket_name = settings.AWS_STORAGE_BUCKET_NAME


def home_redirect_view(request):
    user_id = request.user.id
    user_folder = f"user-{user_id}-files/"

    url = reverse('files:file_manager')
    query = urlencode({'path': user_folder})

    return redirect(f"{url}?{query}")


@csrf_protect
@login_required
def file_manager_view(request):
    storage_strategy = MinIOStorageStrategy()
    service = FileStorageService(storage_strategy)
    try:
        user = request.user
        user_id = user.id
        base_prefix = f"user-{user_id}-files/"

        encoded_path = request.GET.get('path', '')
        current_path = unquote(encoded_path) if encoded_path else ''

        if current_path.startswith(base_prefix):
            relative_path = current_path[len(base_prefix):].lstrip('/')
        elif current_path == base_prefix.rstrip('/'):
            relative_path = ""
        elif not current_path:
            relative_path = ""
        else:
            logger.warning(f"Пользователь {user_id} запросил недопустимый путь: {current_path}")
            return redirect('files:file_manager')

        s3_list_prefix = f"{relative_path}/" if relative_path and not relative_path.endswith('/') else relative_path
        full_s3_prefix = f"{base_prefix}{s3_list_prefix}".lstrip('/').rstrip('/') + '/'
        if s3_list_prefix == "":
            full_s3_prefix = f"{base_prefix}/"

        logger.debug(f"[file_manager] Относительный путь (для breadcrumbs): '{relative_path}'")
        logger.debug(f"[file_manager] Полный S3 префикс (для list_files): '{full_s3_prefix}'")

        items = service.list_files(user_id=user_id, prefix=full_s3_prefix)
        breadcrumbs = _build_breadcrumbs(relative_path)

        context = {
            'items': items,
            'breadcrumbs': breadcrumbs,
            'current_path_relative': relative_path,

        }

        return render(request, "files/file_manager.html", context)

    except Exception as e:
        logger.error(f"Ошибка в file_manager_view: {e}", exc_info=True)
        return render(request, 'files/error.html', {'error_message': 'Ошибка загрузки файлов.'})


@login_required
@csrf_protect
def file_upload_view(request):
    storage_strategy = MinIOStorageStrategy()
    service = FileStorageService(storage_strategy)

    if request.method == 'POST':
        user_id = request.user.id
        files = request.FILES.getlist('files')
        relative_path = request.POST.get('current_path', '').strip()

        current_path = f"user-{user_id}-files/{relative_path}"

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

    return HttpResponseNotAllowed(405)


@login_required
@csrf_protect
def file_download_view(request, s3_key):
    storage_strategy = MinIOStorageStrategy()
    service = FileStorageService(storage_strategy)
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
    storage_strategy = MinIOStorageStrategy()
    service = FileStorageService(storage_strategy)
    """
    Позволяет пользователю удалить файл или папку
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
        return HttpResponseNotAllowed(["POST"])


@login_required
@csrf_protect
def file_rename_view(request):
    storage_strategy = MinIOStorageStrategy()
    service = FileStorageService(storage_strategy)

    if request.method == "POST":
        user_id = request.user.id
        expected_prefix = f"user-{user_id}-files/"

        s3_key = request.POST.get('s3_key', '').strip()
        new_name = request.POST.get('new_name', '').strip()

        if not new_name:
            print(request, 'Имя не может быть пустым')
            return redirect('files:file_manager')

        if not s3_key:
            print(request, 'Не указан объект для переименования')
            return redirect('files:file_manager')

        if not s3_key.startswith(expected_prefix):
            logger.warning(f"Попытка доступа к чужому файлу: {s3_key}")
            raise Http404("Доступ запрещён")

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
            print(f"Ошибка при переименовании {s3_key}: {e}")
            messages.error(request, 'Произошла ошибка на сервере.')

        parent_path = s3_key.rsplit('/', 1)[0] + '/'
        return redirect_with_path(parent_path)

    return redirect('files:file_manager')


@login_required
@csrf_protect
def create_folder_view(request):
    storage_strategy = MinIOStorageStrategy()
    service = FileStorageService(storage_strategy)

    if request.method == "POST":
        user_id = request.user.id
        folder_name = request.POST.get('folder_name', '').strip()
        current_path_encoded = request.POST.get('current_path', '').strip()
        current_path = unquote(current_path_encoded)

        print(f"[create_folder] current_path='{current_path}', folder_name='{folder_name}'")

        if not folder_name:
            messages.error(request, 'Имя папки не может быть пустым')
            return redirect_with_path(current_path or f"user-{user_id}-files/")

        expected_prefix = f"user-{user_id}-files/"

        if current_path and not current_path.endswith('/'):
            current_path += '/'
        elif not current_path or current_path == '':
             current_path = expected_prefix
        full_path = f"{current_path}{folder_name}/"

        try:
            success = service.create_folder(user_id=user_id, folder_s3_key=full_path)
            if success:
                messages.success(request, f'Папка "{folder_name}" создана')
                return redirect_with_path(current_path)
            else:
                messages.error(request, 'Не удалось создать папку')
                return redirect_with_path(current_path)
        except Exception as e:
            print(f"Ошибка при создании папки {full_path}: {e}")
            messages.error(request, 'Ошибка сервера')
            return redirect_with_path(current_path)

    return redirect('files:file_manager')


def redirect_with_path(path: str):
    from django.urls import reverse
    from urllib.parse import quote
    query = f"?path={quote(path)}" if path else ""
    return redirect(f"{reverse('files:file_manager')}{query}")


def _build_breadcrumbs(path: str) -> List[Dict[str, str]]:
    """
    Строит навигационную цепочку (breadcrumbs) из относительного пути внутри пользовательской папки.

    Args:
        path (str): Относительный путь, например, 'docs/projects/'. Может быть пустым.

    Returns:
        list[dict]: Список словарей {'name': '...', 'url_path': '...'}.
                    url_path - это относительный путь до элемента (без user-{id}-files/).
    """
    logger.debug(f"_build_breadcrumbs: input path = '{path}'")
    if not path:
        return []

    parts = path.strip('/').split('/')
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
            'url_path': accumulated_path.rstrip('/')
        })

    logger.debug(f"_build_breadcrumbs: output breadcrumbs = {breadcrumbs}")
    return breadcrumbs
