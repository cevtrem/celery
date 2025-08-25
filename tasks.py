import os
from typing import Tuple

from service.celery_app import make_celery
from service.storage import get_storage


celery_app = make_celery()


@celery_app.task(bind=True, name='tasks.upscale_image')
def upscale_image(self, image_bytes: bytes) -> Tuple[int, int]:
    storage = get_storage()
    if os.getenv('UPSCALE_FAKE') == '1':
        processed = image_bytes
    else:
        from upscale.upscale import upscale_bytes  # Lazy import heavy deps
        processed = upscale_bytes(image_bytes, output_ext='.png')
    storage.set_image(self.request.id, processed, mime_type='image/png')
    return 0, 0


