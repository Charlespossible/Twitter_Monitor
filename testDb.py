# test_database.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from storage import DataStorage
    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/twitter_monitor.db")
    print(f"Testing database connection with URL: {db_url}")
    
    storage = DataStorage(db_url)
    print("✓ Database connection successful")
    
    # Test a simple query
    with storage._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM mentions")
        count = cursor.fetchone()[0]
        print(f"✓ Database query successful. Mentions count: {count}")
    
except Exception as e:
    print(f"✗ Database error: {e}")