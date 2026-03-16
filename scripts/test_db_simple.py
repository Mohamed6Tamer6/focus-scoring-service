from app.database import engine
from sqlalchemy import text
import sys

try:
    print("Attempting to connect to database...")
    with engine.connect() as conn:
        print("Executing SELECT 1...")
        result = conn.execute(text("SELECT 1"))
        print(f"Result: {result.scalar()}")
        print("Success!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
