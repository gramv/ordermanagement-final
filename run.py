from app import create_app, db
from app.extensions import socketio
from app.models import User, Role, Invoice, TempProduct, Category, ProcessingProgress

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Role': Role,
        'Invoice': Invoice,
        'TempProduct': TempProduct,
        'Category': Category,
        'ProcessingProgress': ProcessingProgress
    }

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)