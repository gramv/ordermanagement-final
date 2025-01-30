# app/__init__.py
from flask import Flask
from config import Config
from app.extensions import db, migrate, login
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Block socket.io requests
    @app.route('/socket.io/<path:path>', methods=['GET', 'POST'])
    def block_socketio(path):
        return 'Socket.IO requests are not supported', 404

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.routes.pricing import bp as pricing_bp
    app.register_blueprint(pricing_bp, url_prefix='/pricing')

    from app.routes.invoice import bp as invoice_bp
    if 'invoice.upload_invoice' not in app.view_functions:
        app.register_blueprint(invoice_bp, url_prefix='/invoice')

    # Register CLI commands
    from app import cli
    cli.init_app(app)

    return app