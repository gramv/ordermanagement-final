from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    try:
        connection = db.engine.connect()
        print("Database connection successful!")
        connection.close()
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
