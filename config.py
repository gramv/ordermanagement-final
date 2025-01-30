# config.py
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
import cloudinary
from cloudinary import uploader
import re

# Set up base directory and load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config(object):
    # Application Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # OpenAI API Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Claude API Configuration
    CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')
    
    # DeepSeek API Configuration
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', (
        "postgresql://postgres.xaemejebdiuehjadbxzt:postgres"
        "@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
    ))
    
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "sslmode": "require",
            "gssencmode": "disable",
            "client_encoding": "utf8"
        },
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10
    }
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    
    # Cloudinary Configuration
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
    CLOUDINARY_CLOUD_NAME = None
    CLOUDINARY_API_KEY = None
    CLOUDINARY_API_SECRET = None
    
    if CLOUDINARY_URL:
        # Parse cloudinary URL (format: cloudinary://<api_key>:<api_secret>@<cloud_name>)
        match = re.match(r'cloudinary://(\d+):([^@]+)@(.+)', CLOUDINARY_URL)
        if match:
            api_key, api_secret, cloud_name = match.groups()
            CLOUDINARY_CLOUD_NAME = cloud_name
            CLOUDINARY_API_KEY = api_key
            CLOUDINARY_API_SECRET = api_secret
            
            # Configure cloudinary
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
    
    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_JWT_SECRET = os.environ.get('SUPABASE_JWT_SECRET')
    
    # Email Configuration (if needed)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Application specific settings
    ITEMS_PER_PAGE = 20
    INVOICE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'invoices')
    ALLOWED_INVOICE_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
    
    # Ensure required directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(INVOICE_UPLOAD_FOLDER, exist_ok=True)
    
    # Debug and logging settings
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    @staticmethod
    def init_app(app):
        """Initialize application-specific settings"""
        # Ensure upload directories exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['INVOICE_UPLOAD_FOLDER'], exist_ok=True)
        
        # Configure logging
        if not app.debug and not app.testing:
            import logging
            from logging.handlers import RotatingFileHandler
            
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler(
                'logs/ordermanagement.log',
                maxBytes=10240,
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('OrderManagement startup')