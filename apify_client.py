import asyncio
import logging
from typing import Dict, List, Any, Optional
import aiohttp
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ApifyClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.apify.com/v2"
        self.session = None
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def create_scraping_task(self, urls: List[str], task_type: str = "single") -> str:
        """Create a new scraping task"""
        try:
            session = await self._get_session()
            
            # Prepare task input
            task_input = {
                "urls": urls,
                "task_type": task_type,
                "created_at": datetime.now().isoformat()
            }
            
            # Create task (mock implementation - replace with actual Apify API)
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(urls)}"
            
            logger.info(f"Created scraping task {task_id} for {len(urls)} URLs")
            return task_id
            
        except Exception as e:
            logger.error(f"Error creating scraping task: {e}")
            raise Exception(f"Failed to create scraping task: {str(e)}")
    
    async def get_task_results(self, task_id: str, wait: bool = False, timeout: int = 300) -> Dict[str, Any]:
        """Get task results"""
        try:
            # Mock implementation - replace with actual Apify API calls
            if wait:
                # Simulate waiting for task completion
                await asyncio.sleep(2)
            
            # Mock successful result
            mock_results = {
                "status": "completed",
                "results": [
                    {
                        "success": True,
                        "url": "https://instagram.com/reel/example/",
                        "username": "example_user",
                        "views": 50000,
                        "likes": 1000,
                        "comments": 50,
                        "caption": "Example caption"
                    }
                ],
                "task_info": {
                    "id": task_id,
                    "status": "completed"
                }
            }
            
            logger.info(f"Retrieved results for task {task_id}")
            return mock_results
            
        except Exception as e:
            logger.error(f"Error getting task results for {task_id}: {e}")
            raise Exception(f"Failed to get task results: {str(e)}")
    
    async def get_reel_data(self, shortcode: str) -> Dict[str, Any]:
        """Get individual reel data"""
        try:
            # Mock implementation - replace with actual scraping logic
            mock_data = {
                "shortcode": shortcode,
                "owner_username": "example_user",
                "view_count": 25000,
                "like_count": 500,
                "comment_count": 25,
                "caption": "Example caption",
                "media_url": f"https://instagram.com/reel/{shortcode}/"
            }
            
            logger.info(f"Retrieved reel data for {shortcode}")
            return mock_data
            
        except Exception as e:
            logger.error(f"Error getting reel data for {shortcode}: {e}")
            raise Exception(f"Failed to get reel data: {str(e)}")
    
    async def get_task_status(self) -> Dict[str, Any]:
        """Get overall task system status"""
        try:
            # Mock implementation
            status = {
                "active_tasks": 0,
                "queued_tasks": 0,
                "tasks": []
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            raise Exception(f"Failed to get task status: {str(e)}")
    
    async def close(self):
        """Close the client session"""
        if self.session and not self.session.closed:
            await self.session.close()

# Global client instance
_apify_client = None

def get_apify_client() -> ApifyClient:
    """Get Apify client instance"""
    global _apify_client
    if _apify_client is None:
        import os
        token = os.getenv("APIFY_TOKEN")
        if not token:
            raise ValueError("APIFY_TOKEN environment variable is required")
        _apify_client = ApifyClient(token)
    return _apify_client