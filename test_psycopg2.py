import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def test_psycopg2_connection():
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres.vmkaynbnljwubhxvvflb",
            password=os.getenv('SUPABASE_DB_PASSWORD'),
            host="aws-0-us-east-1.pooler.supabase.com",
            port="6543",
            sslmode="require"
        )
        
        cur = conn.cursor()
        cur.execute('SELECT 1')
        result = cur.fetchone()
        print("Connection successful!")
        print(f"Test query result: {result}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print("Connection failed!")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_psycopg2_connection()