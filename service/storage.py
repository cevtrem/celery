import os
from typing import Optional, Tuple


class ImageStorage:
    def set_image(self, task_id: str, image_bytes: bytes, mime_type: str = 'image/png', ttl_seconds: int = 24 * 3600) -> None:
        raise NotImplementedError

    def get_image(self, task_id: str) -> Optional[Tuple[bytes, str]]:
        raise NotImplementedError


class MemoryStorage(ImageStorage):
    def __init__(self) -> None:
        self._store: dict[str, Tuple[bytes, str]] = {}

    def set_image(self, task_id: str, image_bytes: bytes, mime_type: str = 'image/png', ttl_seconds: int = 24 * 3600) -> None:
        self._store[task_id] = (image_bytes, mime_type)

    def get_image(self, task_id: str) -> Optional[Tuple[bytes, str]]:
        return self._store.get(task_id)


class RedisStorage(ImageStorage):
    def __init__(self, url: str) -> None:
        import redis
        self._client = redis.Redis.from_url(url)

    def set_image(self, task_id: str, image_bytes: bytes, mime_type: str = 'image/png', ttl_seconds: int = 24 * 3600) -> None:
        key = f'processed:{task_id}'
        # Store as raw bytes; store mime in separate key
        pipe = self._client.pipeline(True)
        pipe.set(key, image_bytes, ex=ttl_seconds)
        pipe.set(f'{key}:mime', mime_type, ex=ttl_seconds)
        pipe.execute()

    def get_image(self, task_id: str) -> Optional[Tuple[bytes, str]]:
        key = f'processed:{task_id}'
        image_bytes = self._client.get(key)
        if image_bytes is None:
            return None
        mime = self._client.get(f'{key}:mime')
        mime_type = mime.decode('utf-8') if isinstance(mime, (bytes, bytearray)) else 'image/png'
        return image_bytes, mime_type


_storage: Optional[ImageStorage] = None


def get_storage() -> ImageStorage:
    global _storage
    if _storage is not None:
        return _storage
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        _storage = RedisStorage(redis_url)
    else:
        _storage = MemoryStorage()
    return _storage


