from sqlalchemy import text
from database.connection import get_db_session
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class UserService:
    
    async def create_user(self, user_id: int, username: str = None) -> bool:
        """Create new user if doesn't exist"""
        try:
            async with await get_db_session() as session:
                # Check if user exists
                existing = await session.execute(
                    text("SELECT 1 FROM users WHERE user_id = :u"),
                    {"u": user_id}
                )
                
                if existing.scalar():
                    return False
                
                # Create user
                await session.execute(
                    text("""
                        INSERT INTO users (user_id, username, approved, total_views, total_reels, max_slots, used_slots)
                        VALUES (:u, :n, :a, :v, :r, :m, :s)
                    """),
                    {
                        "u": user_id, 
                        "n": username, 
                        "a": False, 
                        "v": 0, 
                        "r": 0, 
                        "m": 50, 
                        "s": 0
                    }
                )
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data"""
        try:
            async with await get_db_session() as session:
                result = await session.execute(
                    text("""
                        SELECT user_id, username, approved, total_views, total_reels, 
                               max_slots, used_slots, last_submission, created_at
                        FROM users WHERE user_id = :u
                    """),
                    {"u": user_id}
                )
                row = result.fetchone()
                
                if not row:
                    return None
                
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "approved": row[2],
                    "total_views": row[3] or 0,
                    "total_reels": row[4] or 0,
                    "max_slots": row[5] or 50,
                    "used_slots": row[6] or 0,
                    "last_submission": row[7],
                    "created_at": row[8]
                }
                
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def update_user_stats(self, user_id: int, total_views: int = None, 
                               total_reels: int = None, used_slots: int = None) -> bool:
        """Update user statistics"""
        try:
            async with await get_db_session() as session:
                updates = []
                params = {"u": user_id}
                
                if total_views is not None:
                    updates.append("total_views = :tv")
                    params["tv"] = total_views
                
                if total_reels is not None:
                    updates.append("total_reels = :tr")
                    params["tr"] = total_reels
                
                if used_slots is not None:
                    updates.append("used_slots = :us")
                    params["us"] = used_slots
                
                if not updates:
                    return False
                
                updates.append("last_submission = :ls")
                params["ls"] = datetime.now()
                
                query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = :u"
                
                await session.execute(text(query), params)
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating user stats {user_id}: {e}")
            return False
    
    async def approve_user(self, user_id: int) -> bool:
        """Approve user account"""
        try:
            async with await get_db_session() as session:
                await session.execute(
                    text("UPDATE users SET approved = TRUE WHERE user_id = :u"),
                    {"u": user_id}
                )
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error approving user {user_id}: {e}")
            return False
    
    async def ban_user(self, user_id: int) -> bool:
        """Ban user and delete their data"""
        try:
            async with await get_db_session() as session:
                # Add to banned users
                await session.execute(
                    text("INSERT INTO banned_users (user_id) VALUES (:u) ON CONFLICT (user_id) DO NOTHING"),
                    {"u": user_id}
                )
                
                # Delete user data
                tables_to_clean = [
                    "reels", "allowed_accounts", "payment_details", 
                    "account_requests", "referrals", "users"
                ]
                
                for table in tables_to_clean:
                    await session.execute(
                        text(f"DELETE FROM {table} WHERE user_id = :u"),
                        {"u": user_id}
                    )
                
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
            return False
    
    async def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        try:
            async with await get_db_session() as session:
                result = await session.execute(
                    text("SELECT 1 FROM banned_users WHERE user_id = :u"),
                    {"u": user_id}
                )
                return bool(result.scalar())
                
        except Exception as e:
            logger.error(f"Error checking ban status for {user_id}: {e}")
            return False

# Global user service instance
user_service = UserService()

def get_user_service() -> UserService:
    """Get user service instance"""
    return user_service