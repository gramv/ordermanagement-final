import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
# import cloudinary (commented for now)


basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Update this to use Supabase connection
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://postgres:{quote_plus('postgres')}"
        f"@db.xaemejebdiuehjadbxzt.supabase.co:5432/postgres"
    )
    
    # Add SSL configuration for Supabase
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "sslmode": "require"
        }
    }
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Maximum file size
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
    
    # Allowed file extensions for different types
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    ALLOWED_REPORT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
    MAX_REPORT_SIZE = 5 * 1024 * 1024  # 5MB max file size
    
    # Cloudinary configuration (commented for now)
    # CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    # CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    # CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')
    
    @staticmethod
    def init_app(app):
        pass
        # Initialize Cloudinary (commented for now)
        # cloudinary.config(
        #     cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
        #     api_key=app.config['CLOUDINARY_API_KEY'],
        #     api_secret=app.config['CLOUDINARY_API_SECRET'],
        #     secure=True
        # )
