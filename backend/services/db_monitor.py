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
            # Wait 2 minutes between checks (reduced from 5)
            await asyncio.sleep(120)

            # Log pool status
            status = db_service.get_pool_status()
            active = status.get("active_connections", 0)
            total = status.get("maxconn", 0)
            tracked_in_use = status.get("tracked_in_use", 0)
            oldest_age = status.get("oldest_in_use_age", 0)
            leaked_count = status.get("leaked_connections", 0)

            logger.info(f"DB Pool Status: {active}/{total} connections active, {tracked_in_use} tracked in-use")

            # Warn if pool is getting full
            if active > total * 0.8:
                logger.warning(f"High connection pool usage: {active}/{total} connections")

            # Check for leaked connections (in-use >10 minutes)
            if leaked_count > 0:
                logger.warning(f"Detected {leaked_count} connections in use >10 minutes - potential leaks")

            # Check for very old connections
            if oldest_age > 300:  # 5 minutes
                logger.warning(f"Oldest connection in use for {oldest_age:.1f}s")

            # Call prune_old_connections to log potential leaks
            try:
                db_service.prune_old_connections()
            except Exception as e:
                logger.warning(f"Error pruning old connections: {e}")

            # Emergency recovery: Kill PostgreSQL connections that are idle too long
            if leaked_count > 0 or (active >= total):
                logger.warning("Attempting emergency connection recovery")
                try:
                    # Get a fresh connection directly from pool to run admin query
                    conn = db_service._conn()
                    try:
                        with conn.cursor() as cur:
                            # Find and kill connections idle for >30 minutes
                            cur.execute("""
                                SELECT pg_terminate_backend(pid)
                                FROM pg_stat_activity
                                WHERE datname = current_database()
                                  AND pid <> pg_backend_pid()
                                  AND state = 'idle'
                                  AND state_change < (NOW() - INTERVAL '30 minutes')
                            """)
                            terminated = cur.rowcount
                            if terminated > 0:
                                logger.warning(f"Terminated {terminated} idle PostgreSQL connections")
                            conn.commit()
                    finally:
                        db_service._return(conn)
                except Exception as e:
                    logger.error(f"Error during emergency connection recovery: {e}")

            # Reset tracking if severely inconsistent
            if tracked_in_use == 0 and active > 10:
                logger.error(f"Connection tracking lost! {active} active but 0 tracked. Resetting tracking.")
                db_service._connections_in_use.clear()

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
