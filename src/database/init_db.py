"""Database initialization script"""
import asyncio
from src.database.session import init_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def initialize_with_sample_data():
    """Initialize database with sample RAG data"""
    try:
        # Import here to avoid circular imports
        from init_rag_data import create_sample_knowledge_bases
        
        logger.info("Creating sample knowledge bases...")
        await create_sample_knowledge_bases()
        logger.info("Sample data initialization complete!")
        
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        # Don't raise - database tables are still created

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database tables created!")
    
    print("Creating sample knowledge base data...")
    asyncio.run(initialize_with_sample_data())
    print("Database initialization complete!")

