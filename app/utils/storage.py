import os
from werkzeug.utils import secure_filename
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class FileStorage:
    @staticmethod
    def save_file(file, subfolder=''):
        if not file:
            return None
        filename = secure_filename(file.filename)
        folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(folder_path, exist_ok=True)
        filepath = os.path.join(folder_path, filename)
        file.save(filepath)
        return filepath

    @staticmethod
    def delete_file(filepath):
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

CloudinaryStorage = FileStorage