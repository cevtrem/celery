import os
import threading
from typing import Optional

import cv2
import numpy as np
from cv2 import dnn_superres


_scaler_lock = threading.Lock()
_shared_scaler: Optional[dnn_superres.DnnSuperResImpl] = None


def _get_default_model_path() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'EDSR_x2.pb')


def get_or_load_scaler(model_path: Optional[str] = None) -> dnn_superres.DnnSuperResImpl:
    global _shared_scaler
    if _shared_scaler is not None:
        return _shared_scaler
    with _scaler_lock:
        if _shared_scaler is not None:
            return _shared_scaler
        resolved_model_path = model_path or _get_default_model_path()
        scaler = dnn_superres.DnnSuperResImpl_create()
        scaler.readModel(resolved_model_path)
        scaler.setModel("edsr", 2)
        _shared_scaler = scaler
        return _shared_scaler


def upscale(input_path: str, output_path: str, model_path: Optional[str] = None) -> None:
    """
    :param input_path: путь к изображению для апскейла
    :param output_path:  путь к выходному файлу
    :param model_path: путь к ИИ модели. Если не указан, используется локальный EDSR_x2.pb
    :return:
    """

    scaler = get_or_load_scaler(model_path)
    image = cv2.imread(input_path)
    result = scaler.upsample(image)
    cv2.imwrite(output_path, result)


def upscale_bytes(image_bytes: bytes, model_path: Optional[str] = None, output_ext: str = '.png') -> bytes:
    """Апскейлит изображение, переданное в виде байтов, и возвращает байты результата.

    :param image_bytes: содержимое исходного изображения
    :param model_path: путь к ИИ модели. Если не указан, используется локальный EDSR_x2.pb
    :param output_ext: расширение результирующего изображения для кодирования (например, '.png' или '.jpg')
    :return: байты обработанного изображения
    """

    scaler = get_or_load_scaler(model_path)
    np_arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    result = scaler.upsample(image)
    success, buf = cv2.imencode(output_ext, result)
    if not success:
        raise RuntimeError('Failed to encode upscaled image')
    return buf.tobytes()


def example():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(current_dir, 'lama_300px.png')
    dst = os.path.join(current_dir, 'lama_600px.png')
    upscale(src, dst)


if __name__ == '__main__':
    example()