@echo off
REM Скрипт для запуска MinIO сервера

REM Установка переменных окружения
set MINIO_ROOT_USER=minioadmin
set MINIO_ROOT_PASSWORD=minioadmin

REM Переход в директорию с minio.exe (если нужно)
cd /d C:\minio

REM Запуск MinIO сервера
REM Убедитесь, что путь к данным (C:\minio\data) существует
minio.exe server C:\minio\data --console-address ":9001"

REM Пауза, чтобы окно не закрывалось сразу в случае ошибки
pause