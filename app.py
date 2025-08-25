import io
import os
from typing import Tuple

from flask import Flask, jsonify, request, url_for, send_file, abort

from service.celery_app import make_celery
from service.storage import get_storage
from tasks import upscale_image


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))
    app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
    app.config['CELERY_RESULT_BACKEND'] = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')
    app.config['CELERY_TASK_ALWAYS_EAGER'] = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'false').lower() == 'true'

    make_celery(app)

    @app.post('/upscale')
    def post_upscale():
        if 'file' not in request.files:
            return jsonify({'error': 'file field required'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'empty filename'}), 400
        image_bytes: bytes = file.read()

        async_result = upscale_image.delay(image_bytes)
        task_id = async_result.id
        status_url = url_for('get_task', task_id=task_id, _external=True)
        return jsonify({'task_id': task_id, 'status_url': status_url}), 202

    @app.get('/tasks/<task_id>')
    def get_task(task_id: str):
        # Eager mode short-circuit
        if app.config.get('CELERY_TASK_ALWAYS_EAGER'):
            file_url = url_for('get_processed', file=f'{task_id}.png', _external=True)
            return jsonify({'task_id': task_id, 'status': 'SUCCESS', 'file_url': file_url})

        from celery.result import AsyncResult
        from tasks import celery_app

        result = AsyncResult(task_id, app=celery_app)
        response = {'task_id': task_id, 'status': result.status}
        if result.status == 'SUCCESS':
            file_url = url_for('get_processed', file=f'{task_id}.png', _external=True)
            response['file_url'] = file_url
        elif result.status == 'FAILURE':
            response['error'] = str(result.result)
        return jsonify(response)

    @app.get('/processed/<path:file>')
    def get_processed(file: str):
        # Accept either <task_id> or <task_id>.ext
        task_id = file.split('.')[0]
        storage = get_storage()
        data = storage.get_image(task_id)
        if data is None:
            abort(404)
        image_bytes, mime_type = data
        return send_file(io.BytesIO(image_bytes), mimetype=mime_type)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8000)))


