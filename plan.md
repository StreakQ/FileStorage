# Облачное хранилище файлов на Python (под архитектуру MVCS)

## 🧱 Архитектура проекта: MVCS

Проект будет построен по архитектуре **MVCS (Model-View-Controller-Service)**:
- **Model** — отвечает за работу с данными, включая взаимодействие с базой данных и внешними системами (например, S3).
- **View** — отвечает за отображение данных пользователю. В данном случае это HTML-шаблоны.
- **Controller** — обрабатывает входящие HTTP-запросы, вызывает соответствующие методы сервисов и возвращает ответ (в виде страниц или JSON).
- **Service** — бизнес-логика приложения, отделённая от контроллеров для упрощения тестирования и повторного использования.

---

## 🔌 Технологии

- **Backend**: Django
- **Frontend**: HTML/CSS/JS, Bootstrap
- **Базы данных**:
  - MySQL — хранение информации о пользователях
  - Redis — хранение сессий
  - S3 (MinIO) — хранение файлов
- **Тестирование**:
  - `unittest` — модульные и интеграционные тесты
  - `Selenium` — функциональные и UI-тесты
- **Docker Compose** — для запуска всех сервисов локально
- **Build System**: Poetry

---

---

### 🔧 Этап 0: Подготовка окружения

**Цель**: Настроить рабочее пространство для разработки.

#### Действия:
1. Установить:
   - Python 3.8+
   - `pip` (или `poetry`, если предпочитаешь)
   - Git
   - Docker и Docker Compose
2. Создать папку проекта:
   ```bash
   mkdir cloud_file_storage && cd cloud_file_storage
   ```
3. Инициализировать виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или venv\Scripts\activate  # Windows
   ```
4. Установить зависимости:
   ```bash
   pip install django boto3 selenium mysqlclient django-test-plus python-decouple
   ```

---

### 🐳 Этап 1: Настройка Docker Compose (только MySQL)

**Цель**: Запустить базу данных до начала разработки.

#### Действия:
1. Создать `docker-compose.yml`:
   ```yaml
   version: '3.8'
   services:
     db:
       image: mysql:8.0
       environment:
         MYSQL_ROOT_PASSWORD: root
         MYSQL_DATABASE: cloud_db
       ports:
         - "3306:3306"
       volumes:
         - mysql_data:/var/lib/mysql
   volumes:
     mysql_data:
   ```
2. Запустить контейнер:
   ```bash
   docker-compose up -d db
   ```
3. Проверить доступность MySQL (например, через клиент или `telnet`).

---

### 🌐 Этап 2: Инициализация Django-проекта

**Цель**: Создать ядро приложения с правильной структурой.

#### Действия:
1. Создать проект Django:
   ```bash
   django-admin startproject config .
   ```
2. Переместить `settings.py`, `urls.py`, `wsgi.py`, `asgi.py` в папку `config/`
3. Обновить импорты в `manage.py` и `wsgi.py`:
   ```python
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
   ```
4. Настроить `config/settings.py`:
   - Подключение к MySQL (`DATABASES`)
   - Установка `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
   - Использование `python-decouple` для переменных окружения

---

### 👤 Этап 3: Реализация пользователей и аутентификации

**Цель**: Реализовать регистрацию, вход и выход.

#### Действия:
1. Создать приложение `users`:
   ```bash
   python manage.py startapp 1www
   ```
2. Оставить стандартную модель `User` из Django.
3. Создать слои по MVCS:
   - `users/repositories/user_repository.py` — работа с ORM
   - `users/services/auth_service.py` — бизнес-логика
   - `users/views/auth_views.py` — контроллеры (`login`, `register`, `logout`)
   - `users/forms/auth_forms.py` — формы регистрации и входа
4. Создать шаблоны:
   - `templates/login.html`
   - `templates/register.html`
5. Прописать URL-маршруты в `config/urls.py` и `users/urls.py`
6. Выполнить миграции:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

---

### 🧪 Этап 4: Интеграционные тесты (сервис пользователей)

**Цель**: Проверить работу репозитория и сервиса до интеграции с другими системами.

#### Действия:
1. Создать `tests/unit/test_user_repository.py`
2. Использовать `TestCase` и `Testcontainers`:
   - Запуск временного экземпляра MySQL
   - Тест создания пользователя
   - Тест проверки уникальности email и username
3. Покрыть основные кейсы:
   - Успешная регистрация
   - Ошибка при дубликате
   - Авторизация с неверным паролем

---

### 🐳 Этап 5: Добавление MinIO в Docker Compose

**Цель**: Подключить S3-совместимое хранилище для файлов.

#### Действия:
1. Добавить в `docker-compose.yml`:
   ```yaml
   minio:
     image: minio/minio
     ports:
       - "9000:9000"
       - "9001:9001"
     environment:
       MINIO_ROOT_USER: minioadmin
       MINIO_ROOT_PASSWORD: minioadmin
     command: server /data --console-address :9001
     volumes:
       - minio_data:/data
   volumes:
     minio_data:
   ```
2. Запустить:
   ```bash
   docker-compose up -d minio
   ```
3. Открыть консоль MinIO: `http://localhost:9001`
4. Создать бакет `user-files`

---

### 💾 Этап 6: Интеграция с S3 (boto3) и сервис файлов

**Цель**: Реализовать хранение файлов в MinIO.

#### Действия:
1. Настроить `boto3` в Django:
   ```python
   s3 = boto3.client(
       's3',
       endpoint_url='http://minio:9000',
       aws_access_key_id='minioadmin',
       aws_secret_access_key='minioadmin'
   )
   ```
2. Создать приложение `files`:
   ```bash
   python manage.py startapp files
   ```
3. Реализовать слои:
   - `files/repositories/file_repository.py` — операции с S3
   - `files/services/file_service.py` — бизнес-логика (загрузка, удаление, переименование)
4. Поддерживаемые операции:
   - Загрузка файла
   - Получение списка файлов по пути
   - Удаление
   - Переименование (через копирование + удаление)
   - Проверка принадлежности файлов пользователю

---

### 📂 Этап 7: Загрузка и отображение файлов

**Цель**: Реализовать интерфейс для загрузки и просмотра файлов.

#### Действия:
1. Создать контроллеры:
   - `files/views/file_views.py`
   - Главная страница `/` с параметром `?path=...`
2. Реализовать:
   - Форму загрузки файлов (`<input type="file">`)
   - Форму загрузки папок (`webkitdirectory`)
   - Отображение содержимого папки
   - Breadcrumbs (навигационная цепочка)
3. Шаблон `home.html`:
   - Список файлов и папок
   - Меню действий (удалить, переименовать)
4. Ограничить размер загрузки в `settings.py`:
   ```python
   FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 МБ
   DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
   ```

---

### 🔍 Этап 8: Поиск файлов

**Цель**: Реализовать поиск по имени файла.

#### Действия:
1. Создать контроллер `/search/?query=...`
2. Реализовать:
   - Форму поиска на главной странице
   - Отображение результатов
   - Проверка, что пользователь видит только свои файлы
3. Шаблон `search.html`

---

### 🐳 Этап 9: Добавление Redis и настройка сессий

**Цель**: Заменить хранение сессий с БД на Redis.

#### Действия:
1. Добавить в `docker-compose.yml`:
   ```yaml
   redis:
     image: redis:alpine
     ports:
       - "6379:6379"
   ```
2. Запустить:
   ```bash
   docker-compose up -d redis
   ```
3. Установить:
   ```bash
   pip install django-redis
   ```
4. Настроить `settings.py`:
   ```python
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.redis.RedisCache',
           'LOCATION': 'redis://redis:6379/0',
       }
   }
   SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
   SESSION_CACHE_ALIAS = 'default'
   ```
5. Убедиться, что сессии работают

---

### 🧪 Этап 10: Функциональные тесты (Selenium)

**Цель**: Автоматизировать проверку UI.

#### Действия:
1. Создать `tests/functional/test_user_journey.py`
2. Написать тесты:
   - Регистрация → Вход → Загрузка файла → Поиск → Удаление
   - Проверка, что пользователь не видит чужие файлы
3. Использовать `LiveServerTestCase` + `Selenium WebDriver`

---

### 🚀 Этап 11: Деплой на сервер

**Цель**: Развернуть приложение в продакшене.

#### Действия:
1. Арендовать VPS (например, на Hetzner, DigitalOcean)
2. Установить:
   - Ubuntu / Debian
   - Python, pip, git
   - Docker, Docker Compose
3. Скопировать проект:
   ```bash
   git clone https://github.com/yourname/cloud_file_storage.git
   ```
4. Собрать образ Django (при необходимости — через `Dockerfile`)
5. Запустить все сервисы:
   ```bash
   docker-compose up -d
   ```
6. Выполнить:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
7. Настроить Gunicorn + Nginx (опционально, для production)
8. Открыть сайт по IP: `http://$server_ip:8000/`


---

## 🗂️ Структура проекта

```
cloud_file_storage/
│
├── config/                  # Настройки Django (settings.py, urls.py)
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── users/                   # Приложение пользователей
│   ├── migrations/
│   ├── views/
│   │   ├── __init__.py
│   │   └── auth_views.py
│   ├── forms/
│   │   ├── __init__.py
│   │   └── auth_forms.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── auth_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── user_repository.py
│   ├── tests/
│   │   ├── unit/
│   │   └── functional/
│   ├── apps.py              # Автосгенерированный файл
│   └── __init__.py
│
├── core/                    # Основная логика приложения
│   ├── models/
│   │   ├── file.py
│   │   └── folder.py
│   ├── services/
│   │   └── file_service.py
│   ├── repositories/
│   │   └── file_repository.py
│   ├── views/
│   │   └── file_views.py
│   ├── forms/
│   │   └── upload_form.py
│   └── utils/
│       └── s3_utils.py
│
├── templates/               # Шаблоны Jinja2
├── static/                  # Статические файлы
├── media/                   # Локальное хранилище (опционально)
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## ✅ Что должно быть реализовано

| Функция | Статус |
|--------|--------|
| Регистрация и авторизация через Django Auth | ✅ |
| Загрузка файлов и папок через `<input type="file" webkitdirectory>` | ✅ |
| Отображение файлов по пути `/?path=` | ✅ |
| Переименование и удаление файлов | ✅ |
| Поиск файлов | ✅ |
| Интеграция с MinIO через Boto3 | ✅ |
| Сессии через Redis | ✅ |
| Docker Compose для всех сервисов | ✅ |
| Модульные тесты (unittest) | ✅ |
| Функциональные тесты (Selenium) | ✅ |

---

Если хотите, я могу подготовить готовый шаблон проекта с этой структурой, шаблонами, конфигурацией и примерами тестов.  
Нужно ли вам это?