from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.http import Http404
from django.contrib.auth.decorators import login_required
from files.services.fileStorage_service import FileStorageService
import logging
from urllib.parse import unquote, urlencode
from typing import List, Dict

logger = logging.getLogger(__name__)

service = FileStorageService()


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

        items = service.list_files(user_id=user.id, prefix=current_path)
        logger.debug(f"Получено {len(items)} для отображения")

        breadcrumbs = _build_breadcrumbs(current_path)
        print(f"DEBUG: breadcrumbs = {breadcrumbs}")
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


@login_required
@csrf_protect
def file_upload_view(request):
    """
    Позволяет пользователю загрузить файлы в облако
    :param request:
    :return:
    """
    if request.method == "POST":
        user_id = request.user.id
        current_path_form_form = request.POST.get('current_path', '').strip('/')
        uploaded_files = request.FILES.getlist('files')

        for uploaded_file in uploaded_files:
            s3_filename = uploaded_file.name
            if current_path_form_form:
                s3_filename = f"{current_path_form_form}/{s3_filename}"

            service.upload_file(
                user_id=user_id,
                file_obj=uploaded_file,
                filename_in_s3=s3_filename,
            )

            redirect_url = "files:file_manager"
            if current_path_form_form:
                redirect_url = f"{reverse(redirect_url)}?path={current_path_form_form}"
            else:
                redirect_url = f"{reverse(redirect_url)}"
            return redirect(redirect_url)
    else:
        return redirect('files:file_manager')


@login_required
@csrf_protect
def file_download_view(request, s3_key):
    """
    Позволяет пользователю скачать файлы из облака
    :param s3_key:
    :param request:
    """


@login_required
@csrf_protect
def file_delete_view(request, s3_key):
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
def file_rename_view(request, s3_key):
    """
    Позволяет пользователю переименовать файл
    """
    if request.method == "POST":
        user_id = request.user.id
        expected_prefix = f"user-{user_id}-files/"
        new_name = request.POST.get('new_name', '').strip()

        if not new_name:
            return redirect('files:file_manager')

        print("🔧 [DEBUG] new_name:", repr(new_name))

        if not s3_key.startswith(expected_prefix):
            raise Http404("Файл не найден или доступ запрещен")

        try:
            service.rename_object(
                user_id=user_id,
                s3_key=s3_key,
                new_name=new_name,
            )

            return redirect('files:file_manager')

        except Exception as e:
            logger.error(f"Ошибка при переименовании файла {s3_key}: {e}", exc_info=True)

            return redirect('files:file_manager')

    else:

        return redirect('files:file_manager')


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

