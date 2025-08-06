# test_sqlite.py
import sqlite3
import os

def test_sqlite():
    try:
        # Create a test database
        test_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.db")
        
        print(f"Attempting to create test database at: {test_db_path}")
        
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        
        # Create a test table
        cursor.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)')
        
        # Insert a test record
        cursor.execute('INSERT INTO test (name) VALUES (?)', ('test',))
        
        # Query the record
        cursor.execute('SELECT * FROM test')
        result = cursor.fetchone()
        
        print(f"Test successful: {result}")
        
        # Clean up
        conn.close()
        os.remove(test_db_path)
        
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    test_sqlite()