from functools import wraps
from flask import jsonify, current_app
from app.extensions import db

class APIError(Exception):
    """Base exception for API errors"""
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = 'error'
        return rv

def handle_database_error(f):
    """Decorator to handle database errors"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {f.__name__}: {str(e)}")
            raise APIError("Database operation failed", status_code=500)
    return wrapped

def log_api_call(f):
    """Decorator to log API calls"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        current_app.logger.info(f"API call to {f.__name__}")
        return f(*args, **kwargs)
    return wrapped
