#!/usr/bin/env python3
"""
Clear Project Threads Collections Script

This script clears out the project_threads collections from both Qdrant vector database
and Redis cache. It clears the data but preserves the collection structure.
It provides safety features including dry-run mode and confirmation prompts.

Usage:
    python clear_project_threads.py [--dry-run] [--force] [--redis-only] [--qdrant-only]

Options:
    --dry-run       Show what would be cleared without actually clearing
    --force         Skip confirmation prompts
    --redis-only    Only clear Redis cache
    --qdrant-only   Only clear Qdrant collection
    --help          Show this help message
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Optional

import requests
import redis.asyncio as redis

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProjectThreadsCleaner:
    """Cleaner for project_threads collections in Qdrant and Redis"""

    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.qdrant_url = self.settings.qdrant_url
        self.redis_url = self.settings.redis_url
        self.collection_name = "project_threads"
        self.redis_client = None

    async def initialize_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            # Test connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}")
            return False

    async def close_redis(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    def get_qdrant_collections(self) -> List[Dict]:
        """Get all collections from Qdrant"""
        try:
            response = requests.get(f"{self.qdrant_url}/collections", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("result", {}).get("collections", [])
            else:
                logger.error(f"Failed to get collections from Qdrant: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error connecting to Qdrant: {e}")
            return []

    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """Get information about a specific collection"""
        try:
            response = requests.get(f"{self.qdrant_url}/collections/{collection_name}", timeout=10)
            if response.status_code == 200:
                return response.json().get("result", {})
            else:
                logger.warning(f"Collection {collection_name} not found or error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting collection info for {collection_name}: {e}")
            return None

    def clear_qdrant_collection(self, collection_name: str) -> bool:
        """Clear all points from a Qdrant collection (without deleting the collection)"""
        try:
            # Delete all points in the collection using a filter that matches everything
            response = requests.post(
                f"{self.qdrant_url}/collections/{collection_name}/points/delete",
                headers={"Content-Type": "application/json"},
                json={"filter": {"must": []}},  # Empty filter matches all points
                timeout=30
            )
            if response.status_code in [200, 202]:
                logger.info(f"✓ Cleared all points from Qdrant collection: {collection_name}")
                return True
            else:
                logger.error(f"✗ Failed to clear Qdrant collection {collection_name}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error clearing Qdrant collection {collection_name}: {e}")
            return False

    async def get_redis_project_threads(self) -> List[str]:
        """Get all project thread keys from Redis"""
        if not self.redis_client:
            return []

        try:
            # Get all keys that match project thread patterns
            project_thread_keys = []

            # Pattern 1: project_thread:* (direct thread storage)
            thread_keys = await self.redis_client.keys("project_thread:*")
            project_thread_keys.extend([key.decode() if isinstance(key, bytes) else key for key in thread_keys])

            # Pattern 2: project_index:* (project to thread mapping)
            index_keys = await self.redis_client.keys("project_index:*")
            project_thread_keys.extend([key.decode() if isinstance(key, bytes) else key for key in index_keys])

            # Pattern 3: project_events (event queue)
            if await self.redis_client.exists("project_events"):
                project_thread_keys.append("project_events")

            # Pattern 4: project_watch:* (real-time monitoring)
            watch_keys = await self.redis_client.keys("project_watch:*")
            project_thread_keys.extend([key.decode() if isinstance(key, bytes) else key for key in watch_keys])

            return project_thread_keys

        except Exception as e:
            logger.error(f"Error getting Redis project thread keys: {e}")
            return []

    async def delete_redis_keys(self, keys: List[str]) -> int:
        """Delete keys from Redis"""
        if not self.redis_client or not keys:
            return 0

        try:
            deleted_count = await self.redis_client.delete(*keys)
            logger.info(f"✓ Deleted {deleted_count} Redis keys")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting Redis keys: {e}")
            return 0

    async def clear_redis_project_threads(self, dry_run: bool = False) -> Dict:
        """Clear project threads from Redis"""
        result = {
            "redis_connected": False,
            "keys_found": 0,
            "keys_deleted": 0,
            "error": None
        }

        try:
            # Initialize Redis connection
            redis_connected = await self.initialize_redis()
            result["redis_connected"] = redis_connected

            if not redis_connected:
                result["error"] = "Could not connect to Redis"
                return result

            # Get all project thread related keys
            keys = await self.get_redis_project_threads()
            result["keys_found"] = len(keys)

            if keys:
                logger.info(f"Found {len(keys)} Redis keys related to project threads:")
                for key in keys:
                    logger.info(f"  - {key}")

                if not dry_run:
                    deleted_count = await self.delete_redis_keys(keys)
                    result["keys_deleted"] = deleted_count
                else:
                    logger.info("DRY RUN: Would delete these keys")
            else:
                logger.info("No project thread keys found in Redis")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error clearing Redis project threads: {e}")

        finally:
            await self.close_redis()

        return result

    def clear_qdrant_project_threads(self, dry_run: bool = False) -> Dict:
        """Clear project threads from Qdrant"""
        result = {
            "qdrant_connected": False,
            "collection_found": False,
            "collection_cleared": False,
            "points_count": 0,
            "error": None
        }

        try:
            # Check if Qdrant is accessible
            collections = self.get_qdrant_collections()
            result["qdrant_connected"] = True

            # Check if project_threads collection exists
            collection_names = [col.get("name") for col in collections]
            if self.collection_name in collection_names:
                result["collection_found"] = True

                # Get collection info
                collection_info = self.get_collection_info(self.collection_name)
                if collection_info:
                    points_count = collection_info.get("points_count", 0)
                    result["points_count"] = points_count

                    logger.info(f"Found Qdrant collection '{self.collection_name}' with {points_count} points")

                    if not dry_run:
                        # Clear all points from the collection (don't delete the collection itself)
                        cleared = self.clear_qdrant_collection(self.collection_name)
                        result["collection_cleared"] = cleared
                    else:
                        logger.info(f"DRY RUN: Would clear {points_count} points from collection '{self.collection_name}'")
                else:
                    logger.warning(f"Could not get info for collection '{self.collection_name}'")
            else:
                logger.info(f"Collection '{self.collection_name}' not found in Qdrant")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error clearing Qdrant project threads: {e}")

        return result

    async def clear_all_project_threads(self, dry_run: bool = False, redis_only: bool = False, qdrant_only: bool = False) -> Dict:
        """Clear project threads from both Redis and Qdrant"""
        results = {
            "redis": {},
            "qdrant": {},
            "summary": {}
        }

        logger.info("=" * 60)
        logger.info("PROJECT THREADS CLEANUP")
        logger.info("=" * 60)

        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be cleared")
        else:
            logger.info("⚠️  LIVE MODE - Data will be permanently cleared")

        # Clear Redis (unless qdrant_only is specified)
        if not qdrant_only:
            logger.info("\n📦 Clearing Redis project threads...")
            results["redis"] = await self.clear_redis_project_threads(dry_run)

        # Clear Qdrant (unless redis_only is specified)
        if not redis_only:
            logger.info("\n🗄️  Clearing Qdrant project threads...")
            results["qdrant"] = self.clear_qdrant_project_threads(dry_run)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)

        if not qdrant_only:
            redis_result = results["redis"]
            if redis_result["redis_connected"]:
                logger.info(f"Redis: Found {redis_result['keys_found']} keys, deleted {redis_result['keys_deleted']}")
            else:
                logger.warning(f"Redis: Connection failed - {redis_result.get('error', 'Unknown error')}")

        if not redis_only:
            qdrant_result = results["qdrant"]
            if qdrant_result["qdrant_connected"]:
                if qdrant_result["collection_found"]:
                    logger.info(f"Qdrant: Found collection with {qdrant_result['points_count']} points, cleared: {qdrant_result['collection_cleared']}")
                else:
                    logger.info("Qdrant: No project_threads collection found")
            else:
                logger.warning(f"Qdrant: Connection failed - {qdrant_result.get('error', 'Unknown error')}")

        return results


def confirm_action(message: str) -> bool:
    """Ask for user confirmation"""
    response = input(f"{message} (y/N): ").strip().lower()
    return response in ['y', 'yes']


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Clear project_threads collections from Qdrant and Redis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clear_project_threads.py --dry-run          # Show what would be deleted
  python clear_project_threads.py --force            # Delete without confirmation
  python clear_project_threads.py --redis-only       # Only clear Redis
  python clear_project_threads.py --qdrant-only      # Only clear Qdrant
        """
    )

    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be deleted without actually deleting")
    parser.add_argument("--force", action="store_true",
                       help="Skip confirmation prompts")
    parser.add_argument("--redis-only", action="store_true",
                       help="Only clear Redis cache")
    parser.add_argument("--qdrant-only", action="store_true",
                       help="Only clear Qdrant collection")

    args = parser.parse_args()

    # Validate arguments
    if args.redis_only and args.qdrant_only:
        logger.error("Cannot specify both --redis-only and --qdrant-only")
        sys.exit(1)

    # Load settings
    try:
        settings = Settings()
        logger.info(f"Using Qdrant URL: {settings.qdrant_url}")
        logger.info(f"Using Redis URL: {settings.redis_url}")
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        sys.exit(1)

    # Confirmation (unless force or dry-run)
    if not args.dry_run and not args.force:
        action_desc = "Clear project_threads collections"
        if args.redis_only:
            action_desc = "Clear Redis project_threads cache"
        elif args.qdrant_only:
            action_desc = "Clear Qdrant project_threads collection"

        if not confirm_action(f"Are you sure you want to {action_desc}? This action cannot be undone."):
            logger.info("Operation cancelled by user")
            sys.exit(0)

    # Create cleaner and run
    cleaner = ProjectThreadsCleaner(settings)

    try:
        results = await cleaner.clear_all_project_threads(
            dry_run=args.dry_run,
            redis_only=args.redis_only,
            qdrant_only=args.qdrant_only
        )

        # Check for errors
        has_errors = False
        if results["redis"].get("error"):
            has_errors = True
        if results["qdrant"].get("error"):
            has_errors = True

        if has_errors:
            logger.warning("Some operations completed with errors. Check the logs above.")
            sys.exit(1)
        else:
            logger.info("✅ Project threads cleanup completed successfully!")

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
