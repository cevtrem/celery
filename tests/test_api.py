import io
import os

import pytest
from PIL import Image

os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'true'
os.environ['UPSCALE_FAKE'] = '1'

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def make_png_bytes(size=(16, 16), color=(255, 0, 0)) -> bytes:
    img = Image.new('RGB', size, color=color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def test_upscale_flow(client):
    png = make_png_bytes()
    data = {
        'file': (io.BytesIO(png), 'test.png')
    }
    resp = client.post('/upscale', data=data, content_type='multipart/form-data')
    assert resp.status_code == 202
    body = resp.get_json()
    assert 'task_id' in body
    task_id = body['task_id']

    # In eager mode it should be ready immediately
    status = client.get(f'/tasks/{task_id}').get_json()
    assert status['status'] == 'SUCCESS'
    assert 'file_url' in status

    file_resp = client.get(f"/processed/{task_id}.png")
    assert file_resp.status_code == 200
    assert file_resp.mimetype == 'image/png'
    assert len(file_resp.data) > 0


