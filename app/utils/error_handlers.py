from functools import wraps
from flask import current_app, jsonify, request
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
import traceback
from app.extensions import db

class APIError(Exception):
    """Base class for API errors"""
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

def handle_api_error(error):
    """Handler for APIError exceptions"""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

def handle_http_error(error):
    """Handler for HTTPException"""
    response = jsonify({
        'status': 'error',
        'message': str(error),
        'code': error.code
    })
    response.status_code = error.code
    return response

def handle_generic_error(error):
    """Handler for generic exceptions"""
    # Log the full error with traceback
    current_app.logger.error(f"Unhandled exception: {str(error)}")
    current_app.logger.error(traceback.format_exc())
    
    # In production, return generic message
    if current_app.config['ENV'] == 'production':
        message = "An unexpected error occurred"
    else:
        message = str(error)
    
    response = jsonify({
        'status': 'error',
        'message': message
    })
    response.status_code = 500
    return response

def setup_error_handlers(app):
    """Register error handlers with Flask app"""
    app.register_error_handler(APIError, handle_api_error)
    app.register_error_handler(HTTPException, handle_http_error)
    app.register_error_handler(Exception, handle_generic_error)

def handle_database_error(f):
    """Decorator to handle database errors"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {f.__name__}: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            raise APIError(
                message="Database operation failed",
                status_code=500,
                payload={'original_error': str(e)}
            )
    return wrapped

def validate_json_request(schema):
    """Decorator to validate JSON request data against a schema"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not request.is_json:
                raise APIError("Request must be JSON", status_code=400)
            
            data = request.get_json()
            try:
                validated = schema.load(data)
                return f(*args, validated, **kwargs)
            except ValidationError as err:
                raise APIError(
                    message="Invalid request data",
                    status_code=400,
                    payload={'errors': err.messages}
                )
        return wrapped
    return decorator

def log_api_call(f):
    """Decorator to log API calls"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        # Log request
        current_app.logger.info(f"API Call: {request.method} {request.path}")
        current_app.logger.info(f"Headers: {dict(request.headers)}")
        current_app.logger.info(f"Args: {request.args}")
        if request.is_json:
            current_app.logger.info(f"Data: {request.get_json()}")
        
        # Call function
        result = f(*args, **kwargs)
        
        # Log response
        current_app.logger.info(f"Response: {result}")
        return result
    return wrapped

class ErrorHandler:
    """Context manager for handling errors in a block of code"""
    def __init__(self, operation_name):
        self.operation_name = operation_name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            current_app.logger.error(
                f"Error in {self.operation_name}: {str(exc_val)}"
            )
            current_app.logger.error(traceback.format_exc())
            
            if isinstance(exc_val, HTTPException):
                raise exc_val
            elif isinstance(exc_val, APIError):
                raise exc_val
            else:
                raise APIError(
                    message=f"Error during {self.operation_name}",
                    status_code=500,
                    payload={'original_error': str(exc_val)}
                )
        return False

# Example usage in routes:
"""
@app.route('/api/process-invoice', methods=['POST'])
@log_api_call
@validate_json_request(InvoiceSchema())
@handle_database_error
def process_invoice(validated_data):
    with ErrorHandler('invoice processing'):
        # Process invoice
        result = invoice_processor.process(validated_data)
        return jsonify({
            'status': 'success',
            'data': result
        })
"""
