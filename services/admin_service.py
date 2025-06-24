from sqlalchemy import text
from database.connection import get_db_session
from typing import Set
import logging

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, admin_ids: Set[int]):
        self.admin_ids = admin_ids
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin (from env or database)"""
        # Check environment variable first
        if user_id in self.admin_ids:
            return True
        
        # Check database
        try:
            async with await get_db_session() as session:
                result = await session.execute(
                    text("SELECT 1 FROM admins WHERE user_id = :u"),
                    {"u": user_id}
                )
                return bool(result.scalar())
        except Exception as e:
            logger.error(f"Error checking admin status for {user_id}: {e}")
            return False
    
    async def add_admin(self, user_id: int, added_by: int) -> bool:
        """Add new admin to database"""
        try:
            async with await get_db_session() as session:
                # Check if already admin
                existing = await session.execute(
                    text("SELECT 1 FROM admins WHERE user_id = :u"),
                    {"u": user_id}
                )
                
                if existing.scalar():
                    return False
                
                # Add admin
                await session.execute(
                    text("INSERT INTO admins (user_id, added_by) VALUES (:u, :a)"),
                    {"u": user_id, "a": added_by}
                )
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error adding admin {user_id}: {e}")
            return False
    
    async def remove_admin(self, user_id: int) -> bool:
        """Remove admin from database"""
        try:
            async with await get_db_session() as session:
                result = await session.execute(
                    text("DELETE FROM admins WHERE user_id = :u"),
                    {"u": user_id}
                )
                await session.commit()
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error removing admin {user_id}: {e}")
            return False
    
    async def get_all_admins(self) -> list:
        """Get all admins from database"""
        try:
            async with await get_db_session() as session:
                result = await session.execute(
                    text("SELECT user_id, added_by, added_at FROM admins ORDER BY added_at")
                )
                return result.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting all admins: {e}")
            return []

# Global admin service instance
admin_service = None

def get_admin_service(admin_ids: Set[int]) -> AdminService:
    """Get admin service instance"""
    global admin_service
    if admin_service is None:
        admin_service = AdminService(admin_ids)
    return admin_service