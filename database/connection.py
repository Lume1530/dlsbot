import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from database.models import Base
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        self.AsyncSessionLocal = sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
    
    async def init_database(self):
        """Initialize database with all tables and constraints"""
        try:
            async with self.engine.begin() as conn:
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
                
                # Add unique constraints
                await self._add_constraints(conn)
                
                # Insert default config values
                await self._insert_default_config(conn)
                
                logger.info("✅ Database initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def _add_constraints(self, conn):
        """Add database constraints safely"""
        constraints = [
            # Unique constraint for allowed_accounts
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE table_name = 'allowed_accounts' 
                    AND constraint_type = 'UNIQUE' 
                    AND constraint_name = 'allowed_accounts_user_id_insta_handle_key'
                ) THEN
                    ALTER TABLE allowed_accounts 
                    ADD CONSTRAINT allowed_accounts_user_id_insta_handle_key 
                    UNIQUE (user_id, insta_handle);
                END IF;
            END$$;
            """,
            
            # Index for better performance
            """
            CREATE INDEX IF NOT EXISTS idx_reels_user_id ON reels(user_id);
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_reels_shortcode ON reels(shortcode);
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_users_total_views ON users(total_views);
            """,
        ]
        
        for constraint in constraints:
            try:
                await conn.execute(text(constraint))
                logger.info("✅ Constraint added successfully")
            except Exception as e:
                logger.warning(f"⚠️ Constraint creation warning: {e}")
    
    async def _insert_default_config(self, conn):
        """Insert default configuration values"""
        default_configs = [
            ('referral_commission_rate', '0.00'),
            ('min_date', '2024-01-01'),
        ]
        
        for key, value in default_configs:
            try:
                await conn.execute(
                    text("""
                        INSERT INTO config (key, value) 
                        VALUES (:key, :value)
                        ON CONFLICT (key) DO NOTHING
                    """),
                    {"key": key, "value": value}
                )
            except Exception as e:
                logger.warning(f"⚠️ Config insertion warning for {key}: {e}")
    
    async def get_session(self):
        """Get database session"""
        return self.AsyncSessionLocal()
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()

# Global database manager instance
db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get database manager instance"""
    global db_manager
    if db_manager is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        db_manager = DatabaseManager(database_url)
    return db_manager

async def get_db_session():
    """Get database session"""
    manager = get_db_manager()
    return await manager.get_session()