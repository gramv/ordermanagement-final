from app import create_app, db
from sqlalchemy import text

def test_connection():
    app = create_app()
    with app.app_context():
        try:
            # Try to execute a simple query
            result = db.session.execute(text('SELECT 1')).scalar()
            print("Database connection successful!")
            print(f"Test query result: {result}")
            return True
        except Exception as e:
            print("Database connection failed!")
            print(f"Error: {str(e)}")
            return False
        finally:
            db.session.close()

if __name__ == "__main__":
    test_connection()