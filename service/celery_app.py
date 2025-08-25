import os
import types
import uuid
from typing import Any, Callable


celery_app: Any


class _SimpleAsyncResult:
    def __init__(self, task_id: str) -> None:
        self.id = task_id
        self.status = 'SUCCESS'


class _SimpleTaskSelf:
    def __init__(self, task_id: str) -> None:
        self.request = types.SimpleNamespace(id=task_id)


class _SimpleCelery:
    def __init__(self) -> None:
        self.conf = types.SimpleNamespace(task_always_eager=True, task_ignore_result=False)

    def task(self, bind: bool = False, name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            def _call(*args: Any, **kwargs: Any) -> Any:
                task_id = str(uuid.uuid4())
                if bind:
                    self_obj = _SimpleTaskSelf(task_id)
                    return func(self_obj, *args, **kwargs)
                return func(*args, **kwargs)

            def _delay(*args: Any, **kwargs: Any) -> _SimpleAsyncResult:
                task_id = str(uuid.uuid4())
                if bind:
                    self_obj = _SimpleTaskSelf(task_id)
                    func(self_obj, *args, **kwargs)
                else:
                    func(*args, **kwargs)
                return _SimpleAsyncResult(task_id)

            _call.delay = _delay  # type: ignore[attr-defined]
            return _call

        return decorator


def make_celery(flask_app=None) -> Any:
    global celery_app
    task_always_eager = (flask_app and flask_app.config.get('CELERY_TASK_ALWAYS_EAGER')) or os.getenv('CELERY_TASK_ALWAYS_EAGER', 'false').lower() == 'true'

    if task_always_eager:
        celery_app = _SimpleCelery()
        return celery_app

    # Lazy import real Celery to avoid name-collision with project dir during tests
    from celery import Celery  # type: ignore

    broker_url = (flask_app and flask_app.config.get('CELERY_BROKER_URL')) or os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
    result_backend = (flask_app and flask_app.config.get('CELERY_RESULT_BACKEND')) or os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')

    celery_app = Celery('upscale_service', broker=broker_url, backend=result_backend)
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_ignore_result = False
    return celery_app


