"""Database initialization script"""
from src.database.session import init_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    print("Initializing database...")
    try:
        init_db()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()

