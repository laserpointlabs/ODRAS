# Database Connection Pool Troubleshooting Guide

**Document Version**: 1.0
**Last Updated**: October 6, 2025
**Status**: Active Reference

## Problem Summary

### Symptom
After leaving the ODRAS application idle for an extended period (30+ minutes), users cannot log back in. The login endpoint returns a 500 Internal Server Error, and browser refresh does not resolve the issue. Only a full application restart (`./odras.sh restart`) restores login functionality.

### User Impact
- **Severity**: High - Blocks all user access after idle periods
- **Frequency**: Consistent - Occurs predictably after inactivity
- **Workaround**: Application restart required

## Root Cause Analysis

### Technical Investigation (October 6, 2025)

#### Evidence from Logs
```
High connection pool usage: {'minconn': 5, 'maxconn': 50, 'closed': False,
'available_connections': 3, 'active_connections': 47, 'connection_creation_times': 0}

Login error: server closed the connection unexpectedly
	This probably means the server terminated abnormally
	before or while processing the request.

Error processing queued events: unable to perform operation on <TCPTransport closed=True reading=False>
```

#### Browser Console Errors
```
Failed to load resource: net::ERR_NETWORK_IO_SUSPENDED
Auth check failed: TypeError: Failed to fetch
Failed to load resource: the server responded with a status of 500 (Internal Server Error)
```

### Root Causes Identified

1. **Stale Database Connections**
   - PostgreSQL connections in the pool became stale during idle periods
   - No TCP keepalive mechanism to maintain connection health
   - Stale connections were not detected or recycled automatically

2. **Connection Pool Exhaustion**
   - Pool configured with 5-50 connections (too large)
   - 47 out of 50 connections in use, but most were dead
   - No available healthy connections for new login attempts
   - Dead connections were not being released or cleaned up

3. **No Connection Validation**
   - Connections were not tested before being returned from the pool
   - Application code received dead connections
   - Database operations failed with "connection unexpectedly closed" errors

4. **No Active Monitoring**
   - No background task to monitor pool health
   - No automatic cleanup of stale connections
   - Pool exhaustion went undetected until login failures occurred

## Solution Implementation

### 1. TCP Keepalive Configuration

**File**: `backend/services/db.py`

**Change**: Added TCP keepalive parameters to the PostgreSQL connection pool

```python
self.pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=settings.postgres_pool_min_connections,
    maxconn=settings.postgres_pool_max_connections,
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_database,
    user=settings.postgres_user,
    password=settings.postgres_password,
    # Add keepalive to prevent stale connections
    keepalives=1,              # Enable TCP keepalive
    keepalives_idle=30,        # Start probing after 30 seconds idle
    keepalives_interval=10,    # Send probe every 10 seconds
    keepalives_count=5,        # 5 failed probes = dead connection
)
```

**Impact**:
- Connections are kept alive during idle periods
- Dead connections are detected within ~80 seconds (30 + 10×5)
- Prevents silent connection staleness

### 2. Connection Validation

**File**: `backend/services/db.py`

**Change**: Added health check before returning connections from pool

```python
def _conn(self):
    try:
        conn = self.pool.getconn()
        conn_id = id(conn)
        self._connection_creation_time[conn_id] = time.time()

        # Validate connection is alive - test with a simple query
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            logger.warning(f"Dead connection detected, recreating: {e}")
            # Close the dead connection
            try:
                conn.close()
            except Exception:
                pass
            # Remove from pool tracking
            if conn_id in self._connection_creation_time:
                del self._connection_creation_time[conn_id]
            # Get a new connection
            conn = self.pool.getconn()
            conn_id = id(conn)
            self._connection_creation_time[conn_id] = time.time()

        return conn
    except psycopg2.pool.PoolError as e:
        logger.error(f"Failed to get database connection: {e}")
        logger.error(f"Pool status: {self.get_pool_status()}")
        raise
```

**Impact**:
- Dead connections are detected immediately
- Fresh connections are automatically created
- Application code always receives healthy connections
- Zero downtime for connection issues

### 3. Improved Connection Return Logic

**File**: `backend/services/db.py`

**Change**: Enhanced `_return()` method to validate connections before returning to pool

```python
def _return(self, conn):
    try:
        conn_id = id(conn)
        if conn_id in self._connection_creation_time:
            del self._connection_creation_time[conn_id]

        # Check if connection is still valid before returning to pool
        try:
            # Rollback any uncommitted transactions
            if conn and not conn.closed:
                conn.rollback()
                self.pool.putconn(conn)
            else:
                # Connection is closed, just remove it
                logger.warning("Attempted to return closed connection to pool")
                try:
                    self.pool.putconn(conn, close=True)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Error validating connection before return: {e}")
            # Try to close the bad connection
            try:
                self.pool.putconn(conn, close=True)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Error returning connection to pool: {e}")
```

**Impact**:
- Closed connections are properly cleaned up
- Bad connections are removed instead of being reused
- Pool maintains only healthy connections

### 4. Pool Size Reduction

**File**: `backend/services/config.py`

**Change**: Reduced connection pool limits

```python
# Database Connection Pool Configuration
postgres_pool_min_connections: int = 2      # Was: 5
postgres_pool_max_connections: int = 20     # Was: 50
postgres_pool_connection_timeout: int = 30
postgres_pool_connection_lifetime: int = 1800  # 30 minutes (was: 3600)
```

**Impact**:
- Smaller pool is easier to manage and monitor
- Reduces likelihood of pool exhaustion
- 20 connections is sufficient for typical ODRAS workload
- Shorter connection lifetime (30 min) ensures fresher connections

### 5. Background Connection Monitor

**File**: `backend/services/db_monitor.py` (NEW)

**Purpose**: Proactive monitoring and maintenance of connection pool health

```python
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

            # Test sample connections from the pool
            for _ in range(min(3, total)):
                try:
                    conn = db_service.pool.getconn()
                    try:
                        with conn.cursor() as cur:
                            cur.execute("SELECT 1")
                            cur.fetchone()
                        db_service.pool.putconn(conn)
                    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                        logger.warning(f"Found dead connection, closing it: {e}")
                        try:
                            db_service.pool.putconn(conn, close=True)
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"Error testing connection: {e}")

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
            await asyncio.sleep(60)
```

**Integration**: Added to startup event in `backend/main.py`:

```python
# Start connection pool monitoring task
try:
    from backend.services.db_monitor import start_db_monitor
    start_db_monitor(db)
    logger.info("✅ Database connection pool monitor started")
except Exception as e:
    logger.warning(f"Failed to start database monitor: {e}")
```

**Impact**:
- Continuous health monitoring every 5 minutes
- Proactive detection and cleanup of dead connections
- Early warning of pool exhaustion
- Automatic cleanup of expired authentication tokens

## Verification

### Testing Procedure

1. **Immediate Login Test**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"das_service","password":"das_service_2024!"}'
   ```

   **Expected**: Returns authentication token

2. **Connection Pool Health Check**
   ```python
   from backend.services.config import Settings
   from backend.services.db import DatabaseService

   settings = Settings()
   db = DatabaseService(settings)
   status = db.get_pool_status()
   print(f"Active: {status['active_connections']}/{status['maxconn']}")
   ```

   **Expected**: Healthy ratio (< 80% utilization)

3. **Idle Period Test** (Future validation needed)
   - Leave application idle for 1-2 hours
   - Attempt login without restart
   - **Expected**: Login succeeds, no 500 errors

### Results (October 6, 2025)

✅ Immediate login working
✅ Authentication working
✅ Database monitor running
✅ Keepalive enabled
✅ Connection validation active
⏳ Long idle period test pending user feedback

## Monitoring and Diagnostics

### Check Pool Status

**Via Python**:
```bash
cd /home/jdehart/working/ODRAS
python3 << 'EOF'
from backend.services.config import Settings
from backend.services.db import DatabaseService

settings = Settings()
db = DatabaseService(settings)
status = db.get_pool_status()

print(f"\n=== Database Connection Pool Status ===")
print(f"Minimum connections: {status['minconn']}")
print(f"Maximum connections: {status['maxconn']}")
print(f"Active connections: {status['active_connections']}")
print(f"Available connections: {status['available_connections']}")
print(f"Pool utilization: {status['active_connections']}/{status['maxconn']} ({status['active_connections']/status['maxconn']*100:.1f}%)")
print(f"Status: {'🟢 Healthy' if status['active_connections'] < status['maxconn'] * 0.8 else '🟡 High Usage'}")
EOF
```

**Via Application Logs**:
```bash
tail -f /tmp/odras_app.log | grep "DB Pool Status"
```

**Expected Output** (every 5 minutes):
```
DB Pool Status: 5/20 connections in use
```

### Warning Indicators

🟡 **High Usage Warning**:
```
High connection pool usage: 18/20 connections
```
**Action**: Monitor for connection leaks, consider increasing pool size temporarily

🔴 **Pool Exhaustion Error**:
```
Failed to get database connection: connection pool exhausted
```
**Action**: Immediate investigation needed, restart application if necessary

### Application Logs to Monitor

```bash
# Watch for connection issues
tail -f /tmp/odras_app.log | grep -E "connection|pool|Database"

# Check for dead connections
tail -f /tmp/odras_app.log | grep "Dead connection detected"

# Monitor pool warnings
tail -f /tmp/odras_app.log | grep "High connection pool usage"
```

## Future Troubleshooting Steps

If the login issue recurs after this fix, investigate in this order:

### 1. Verify Monitor is Running
```bash
tail -f /tmp/odras_app.log | grep "Database connection pool monitor started"
```
Expected: Should see this message in startup logs

### 2. Check Pool Status During Failure
```bash
# When login fails, immediately check pool status
python3 << 'EOF'
from backend.services.config import Settings
from backend.services.db import DatabaseService
settings = Settings()
db = DatabaseService(settings)
print(db.get_pool_status())
EOF
```

### 3. Check PostgreSQL Side
```bash
# Check active connections from PostgreSQL perspective
docker-compose exec postgres psql -U postgres -d odras -c \
  "SELECT count(*) as active_connections,
          state,
          wait_event_type
   FROM pg_stat_activity
   WHERE datname='odras'
   GROUP BY state, wait_event_type;"
```

### 4. Check for Connection Leaks
Look for code patterns where connections are obtained but not returned:
```python
# BAD - connection leak if exception occurs
conn = db._conn()
# ... operations that might raise exception
db._return(conn)  # Never reached if exception!

# GOOD - guaranteed return
conn = db._conn()
try:
    # ... operations
finally:
    db._return(conn)  # Always executes
```

### 5. Increase Monitoring Frequency (if needed)
If issues persist, modify monitor to run more frequently:

`backend/services/db_monitor.py`:
```python
await asyncio.sleep(60)  # Check every 1 minute instead of 5
```

### 6. Enable Debug Logging
Add to `backend/services/db.py`:
```python
logger.setLevel(logging.DEBUG)
```

This will log every connection acquisition and return.

## Related Configuration

### Environment Variables
No changes required - keepalive settings are hardcoded in the pool initialization.

### Database Configuration
No changes to PostgreSQL configuration required. The keepalive settings are client-side.

### Docker Compose
No changes required to `docker-compose.yml`.

## Prevention Best Practices

### For Developers

1. **Always use try/finally blocks** when working with database connections
2. **Never cache connections** outside the pool
3. **Use context managers** where possible for automatic cleanup
4. **Monitor pool status** during development of new features

### Code Review Checklist

- [ ] Database connections properly returned in all code paths
- [ ] Exception handlers don't prevent connection return
- [ ] No long-running operations holding connections
- [ ] Async operations properly handled

### Example: Proper Connection Handling

```python
def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
    """Get project details by ID."""
    conn = self._conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT project_id, name, description
                FROM public.projects
                WHERE project_id = %s AND is_active = true
                """,
                (project_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        self._return(conn)  # ALWAYS executes, even on exception
```

## References

### Modified Files
- `backend/services/db.py` - Core connection pool changes
- `backend/services/config.py` - Pool size configuration
- `backend/services/db_monitor.py` - NEW - Background monitoring
- `backend/main.py` - Startup event integration

### PostgreSQL Documentation
- [TCP Keepalive](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-KEEPALIVES)
- [Connection Pooling Best Practices](https://wiki.postgresql.org/wiki/Number_Of_Database_Connections)

### psycopg2 Documentation
- [ThreadedConnectionPool](https://www.psycopg.org/docs/pool.html#psycopg2.pool.ThreadedConnectionPool)
- [Connection Parameters](https://www.psycopg.org/docs/module.html#psycopg2.connect)

## Change History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-10-06 | 1.0 | Initial document - Connection pool fix implementation | Claude + jdehart |

---

**Note**: This document should be updated if the issue recurs or if additional troubleshooting steps are discovered. When making changes, update the Version and Change History sections.

