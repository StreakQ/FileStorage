import os
import django
from pathlib import Path
import tempfile # Импортируем здесь, чтобы использовать внутри функции

# 1. Укажите путь к вашему settings.py (относительно этого скрипта)
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings') # Убедитесь, что 'config.settings' правильный путь

# 2. Настройте Django
django.setup() # <- Эта строка критически важна и должна быть выполнена ДО обращения к settings

# --- ИМПОРТ МОДУЛЕЙ ПОСЛЕ django.setup() ---
# (Хотя импорт модуля сам по себе не должен вызывать обращение к settings до создания экземпляра)
from files.services.file_storage_service import FileStorageService
# --- ЛОГИКА ТЕСТИРОВАНИЯ ВНУТРИ ФУНКЦИИ ---
def run_tests():
    print("--- Тестирование подключения к MinIO ---")
    try:
        # Создаем экземпляр сервиса
        # (Это вызовет _ensure_bucket_exists и проверит подключение)
        service = FileStorageService() # <-- Теперь это происходит ПОСЛЕ django.setup()
        print("✅ Сервис FileStorageService инициализирован, бакет проверен/создан.")

    except Exception as e:
        print(f"❌ Ошибка инициализации сервиса: {e}")
        return # Прекращаем тест, если не удалось подключиться

    # --- Тестовая загрузка файла ---
    print("\n--- Тестовая загрузка файла ---")
    user_id_to_test = 1 # ВАЖНО: ЗАМЕНИТЕ НА СУЩЕСТВУЮЩИЙ ID ПОЛЬЗОВАТЕЛЯ!
    filename_in_s3 = "test_folder/test_file_from_script.txt"

    # Создаем временный файл для теста
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
        temp_file.write(b"ASCII")
        temp_file_path = temp_file.name

    try:
        with open(temp_file_path, 'rb') as file_obj:
            success = service.upload_file(user_id_to_test, file_obj, filename_in_s3)
        if success:
            print(f"✅ Файл успешно загружен как {filename_in_s3} для пользователя {user_id_to_test}")
        else:
            print(f"❌ Ошибка загрузки файла для пользователя {user_id_to_test}")
    except Exception as e:
        print(f"❌ Исключение при загрузке файла: {e}")

    # --- Тестовое получение списка файлов ---
    print("\n--- Тестовое получение списка файлов ---")
    try:
        # Проверим корень папки пользователя
        items_root = service.list_files(user_id_to_test, prefix="")
        print(f"📁 Список файлов в корне для пользователя {user_id_to_test}: {len(items_root)} элементов")
        for item in items_root:
             print(f"   - {item['type']}: {item['name']}")

        # Проверим подпапку, где мы только что загрузили файл
        items_in_test_folder = service.list_files(user_id_to_test, prefix="test_folder/")
        print(f"📁 Список файлов в 'test_folder/' для пользователя {user_id_to_test}: {len(items_in_test_folder)} элементов")
        for item in items_in_test_folder:
             print(f"   - {item['type']}: {item['name']}")

    except Exception as e:
        print(f"❌ Исключение при получении списка файлов: {e}")

    # --- Тестовое удаление файла ---
    print("\n--- Тестовое удаление файла ---")
    try:
        success_delete = service.delete_object(user_id_to_test, filename_in_s3)
        if success_delete:
            print(f"✅ Файл {filename_in_s3} успешно удален для пользователя {user_id_to_test}")
        else:
            print(f"❌ Ошибка удаления файла {filename_in_s3} для пользователя {user_id_to_test}")
    except Exception as e:
        print(f"❌ Исключение при удалении файла: {e}")

    # Удаляем временный файл на диске (для чистоты)
    import os
    os.unlink(temp_file_path)
    print("\n🧹 Временный файл на диске удален.")

    print("\n--- Тестирование завершено ---")

# --- ВАЖНО: Запускаем тесты ТОЛЬКО если скрипт запущен напрямую ---
if __name__ == "__main__":
    run_tests() # <-- Вызов функции происходит ПОСЛЕ django.setup()
