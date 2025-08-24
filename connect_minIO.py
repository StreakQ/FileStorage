import os
import django
from django.conf import settings
# from decouple import config # Импортируем config для загрузки из .env

# 1. Укажите путь к вашему settings.py
# Предположим, ваш manage.py находится в C:\PycharmProjects\FileStorage\
# и settings.py в C:\PycharmProjects\FileStorage\config\settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 2. Загрузите настройки из .env (если они используются напрямую в settings.py)
# Этот шаг может быть не нужен, если settings.py уже использует decouple внутри себя.
# Но если вы хотите использовать config напрямую здесь, импортируйте его.
from decouple import Config, RepositoryEnv
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / "env" / "local.env" # Убедитесь, что путь правильный
if ENV_PATH.exists():
    env_config = Config(RepositoryEnv(str(ENV_PATH)))
    # Теперь вы можете использовать env_config('MINIO_ROOT_USER') и т.д.
else:
    raise FileNotFoundError(f".env file not found at {ENV_PATH}")

# 3. Настройте Django
django.setup() # <- Эта строка критически важна

# Теперь можно безопасно импортировать settings и использовать их
# Импортируем boto3 и другие модули ПОСЛЕ django.setup()
import boto3
from botocore.exceptions import ClientError

# --- Пример использования настроек из settings.py ---
# Убедитесь, что в вашем config/settings.py определены эти переменные
# используя decouple, как вы показали:
# from decouple import config
# AWS_ACCESS_KEY_ID = config('MINIO_ROOT_USER')
# AWS_SECRET_ACCESS_KEY = config('MINIO_ROOT_PASSWORD')
# AWS_S3_ENDPOINT_URL = config('MINIO_ENDPOINT_URL')
# ...

try:
    s3_client = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL, # Теперь это должно работать
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        # signature_version=settings.AWS_S3_SIGNATURE_VERSION # Обычно не требуется для MinIO
    )

    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Бакет {bucket_name} уже существует.")
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            print(f"Бакет {bucket_name} не найден. Создаю...")
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Бакет {bucket_name} успешно создан.")
        else:
            print(f"Ошибка при проверке/создании бакета {bucket_name}: {e}")

except Exception as e: # Более общий перехват для ошибок настройки
     print(f"Произошла ошибка: {e}")
