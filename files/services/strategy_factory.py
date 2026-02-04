from .storage.minio_strategy import MinIOStorageStrategy

STORAGE_BACKEND = 'minio'


def get_storage_strategy():
    if STORAGE_BACKEND == 'minio':
        return MinIOStorageStrategy()
    else:
        raise ValueError(f'Неизвестная стратегия: {STORAGE_BACKEND}')