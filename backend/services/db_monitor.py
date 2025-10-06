"""
Database Connection Pool Monitor
Periodically checks and cleans stale connections to prevent pool exhaustion.
"""

import asyncio
import logging
import psycopg2
from typing import Optional

logger = logging.getLogger(__name__)

_monitor_task: Optional[asyncio.Task] = None


async def db_monitor_task(db_service):
    """Background task to monitor and clean database connection pool."""
    while True:
        try:
            # Wait 5 minutes between checks
            await asyncio.sleep(300)

            # Log pool status
            status = db_service.get_pool_status()
            active = status.get("active_connections", 0)
            total = status.get("maxconn", 0)

            logger.info(f"DB Pool Status: {active}/{total} connections in use")

            # Warn if pool is getting full
            if active > total * 0.8:
                logger.warning(f"High connection pool usage: {active}/{total} connections")

            # Try to clean up stale connections
            try:
                # Test a few connections from the pool
                for _ in range(min(3, total)):
                    try:
                        conn = db_service.pool.getconn()
                        try:
                            # Test if connection is alive
                            with conn.cursor() as cur:
                                cur.execute("SELECT 1")
                                cur.fetchone()
                            # Connection is good, return it
                            db_service.pool.putconn(conn)
                        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                            logger.warning(f"Found dead connection, closing it: {e}")
                            try:
                                db_service.pool.putconn(conn, close=True)
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning(f"Error testing connection: {e}")

            except Exception as e:
                logger.error(f"Error cleaning connection pool: {e}")

            # Clean up expired auth tokens
            from backend.services.auth import cleanup_expired_tokens
            try:
                cleanup_expired_tokens()
            except Exception as e:
                logger.warning(f"Error cleaning expired tokens: {e}")

        except asyncio.CancelledError:
            logger.info("Database monitor task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in database monitor: {e}")
            # Continue monitoring even if there's an error
            await asyncio.sleep(60)


def start_db_monitor(db_service):
    """Start the database connection pool monitor."""
    global _monitor_task
    if _monitor_task is None or _monitor_task.done():
        _monitor_task = asyncio.create_task(db_monitor_task(db_service))
        logger.info("Database connection pool monitor started")


def stop_db_monitor():
    """Stop the database connection pool monitor."""
    global _monitor_task
    if _monitor_task and not _monitor_task.done():
        _monitor_task.cancel()
        logger.info("Database connection pool monitor stopped")

