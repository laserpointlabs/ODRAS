"""
EventCapture2 Background Worker

Processes queued events from EventCapture2 and routes them to available DAS systems
for integration with project threads.

Architecture:
✅ Events are queued by middleware/endpoints for non-blocking performance
✅ Worker processes events in background
✅ Events are routed to DAS2 first, then DAS1 as fallback
✅ Only events with existing project threads are routed
✅ Rich event summaries are preserved in project threads
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EventCapture2Worker:
    """Background worker that processes EventCapture2 events"""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.running = False
        self.worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background worker"""
        if self.running:
            logger.warning("EventCapture2 worker already running")
            return

        if not self.redis:
            logger.warning("EventCapture2 worker cannot start - no Redis client")
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("EventCapture2 background worker started")

    async def stop(self):
        """Stop the background worker"""
        self.running = False

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        logger.info("EventCapture2 background worker stopped")

    async def _worker_loop(self):
        """Main worker loop that processes events"""
        logger.info("EventCapture2 worker loop started")

        while self.running:
            try:
                # Get EventCapture2 instance
                from backend.services.eventcapture2 import get_event_capture
                event_capture = get_event_capture()

                if event_capture:
                    # Process queued events (this handles routing to DAS systems)
                    processed = await event_capture.process_queued_events()

                    if processed > 0:
                        logger.debug(f"EventCapture2 worker processed {processed} events")

                # Sleep between processing cycles
                await asyncio.sleep(1)  # Process every second

            except asyncio.CancelledError:
                logger.info("EventCapture2 worker cancelled")
                break
            except Exception as e:
                logger.error(f"EventCapture2 worker error: {e}")
                await asyncio.sleep(5)  # Wait longer on errors

    async def process_batch(self, max_events: int = 10) -> int:
        """Process a batch of events manually (for testing/debugging)"""
        try:
            from backend.services.eventcapture2 import get_event_capture
            event_capture = get_event_capture()

            if not event_capture:
                logger.warning("EventCapture2 not available for batch processing")
                return 0

            processed = 0
            for _ in range(max_events):
                # Process one event at a time
                batch_processed = await event_capture.process_queued_events()
                if batch_processed == 0:
                    break  # No more events
                processed += batch_processed

            return processed

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return 0


# Global worker instance
worker: Optional[EventCapture2Worker] = None


async def start_eventcapture2_worker(redis_client=None):
    """Start the global EventCapture2 worker"""
    global worker

    if worker and worker.running:
        logger.warning("EventCapture2 worker already started")
        return

    worker = EventCapture2Worker(redis_client)
    await worker.start()


async def stop_eventcapture2_worker():
    """Stop the global EventCapture2 worker"""
    global worker

    if worker:
        await worker.stop()
        worker = None


def get_worker() -> Optional[EventCapture2Worker]:
    """Get the global worker instance"""
    return worker
