"""
Real-Time Event Bus for ODRAS Project Lattice

Provides real-time event delivery for project-to-project communication.
Extends the existing EventSubscriptionService with live event broadcasting.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LiveEvent:
    """Live event for real-time delivery."""
    event_id: str
    source_project_id: str
    event_type: str
    event_data: Dict[str, Any]
    timestamp: datetime
    created_by: Optional[str] = None


class EventBus:
    """
    Real-time event bus for project lattice communication.
    
    Provides:
    - Real-time event delivery to subscribers
    - Event queuing and processing
    - WebSocket integration for live updates
    - Event persistence for audit trail
    """
    
    def __init__(self):
        self.subscribers: Dict[str, Set[Callable]] = {}  # event_type -> set of callbacks
        self.project_subscribers: Dict[str, Set[Callable]] = {}  # project_id -> set of callbacks
        self.event_queue: List[LiveEvent] = []
        self.processing_events = False
        self.websocket_connections: Set[Any] = set()
    
    def subscribe_to_event_type(self, event_type: str, callback: Callable) -> Callable:
        """
        Subscribe to all events of a specific type.
        
        Args:
            event_type: Event type to subscribe to
            callback: Function to call when event occurs
            
        Returns:
            Unsubscribe function
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()
        
        self.subscribers[event_type].add(callback)
        logger.info(f"Subscribed to event type: {event_type}")
        
        # Return unsubscribe function
        def unsubscribe():
            if event_type in self.subscribers:
                self.subscribers[event_type].discard(callback)
                if not self.subscribers[event_type]:
                    del self.subscribers[event_type]
        
        return unsubscribe
    
    def subscribe_to_project_events(self, project_id: str, callback: Callable) -> Callable:
        """
        Subscribe to all events from a specific project.
        
        Args:
            project_id: Project to subscribe to
            callback: Function to call when event occurs
            
        Returns:
            Unsubscribe function
        """
        if project_id not in self.project_subscribers:
            self.project_subscribers[project_id] = set()
        
        self.project_subscribers[project_id].add(callback)
        logger.info(f"Subscribed to project events: {project_id}")
        
        # Return unsubscribe function
        def unsubscribe():
            if project_id in self.project_subscribers:
                self.project_subscribers[project_id].discard(callback)
                if not self.project_subscribers[project_id]:
                    del self.project_subscribers[project_id]
        
        return unsubscribe
    
    def add_websocket_connection(self, websocket):
        """Add WebSocket connection for real-time updates."""
        self.websocket_connections.add(websocket)
        logger.info(f"Added WebSocket connection. Total: {len(self.websocket_connections)}")
    
    def remove_websocket_connection(self, websocket):
        """Remove WebSocket connection."""
        self.websocket_connections.discard(websocket)
        logger.info(f"Removed WebSocket connection. Total: {len(self.websocket_connections)}")
    
    async def publish_event(
        self,
        source_project_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish an event to all subscribers.
        
        Args:
            source_project_id: Project publishing the event
            event_type: Type of event
            event_data: Event payload
            created_by: User who triggered the event
            
        Returns:
            Result dictionary with delivery information
        """
        try:
            # Create event
            event = LiveEvent(
                event_id=f"evt_{int(time.time() * 1000)}_{len(self.event_queue)}",
                source_project_id=source_project_id,
                event_type=event_type,
                event_data=event_data,
                timestamp=datetime.now(),
                created_by=created_by
            )
            
            # Add to queue for processing
            self.event_queue.append(event)
            
            # Process events asynchronously
            if not self.processing_events:
                asyncio.create_task(self._process_event_queue())
            
            # Count subscribers
            type_subscribers = len(self.subscribers.get(event_type, set()))
            project_subscribers = len(self.project_subscribers.get(source_project_id, set()))
            total_subscribers = type_subscribers + project_subscribers
            
            logger.info(f"Event queued: {event_type} from {source_project_id} -> {total_subscribers} subscribers")
            
            return {
                "success": True,
                "event_id": event.event_id,
                "subscribers_notified": total_subscribers,
                "event_type": event_type
            }
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _process_event_queue(self):
        """Process queued events asynchronously."""
        self.processing_events = True
        
        while self.event_queue:
            event = self.event_queue.pop(0)
            await self._deliver_event(event)
            
            # Small delay to simulate processing time
            await asyncio.sleep(0.1)
        
        self.processing_events = False
    
    async def _deliver_event(self, event: LiveEvent):
        """Deliver event to all subscribers."""
        delivered_count = 0
        
        # Deliver to event type subscribers
        if event.event_type in self.subscribers:
            for callback in self.subscribers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                    delivered_count += 1
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")
        
        # Deliver to project subscribers
        if event.source_project_id in self.project_subscribers:
            for callback in self.project_subscribers[event.source_project_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                    delivered_count += 1
                except Exception as e:
                    logger.error(f"Error in project callback: {e}")
        
        # Broadcast to WebSocket connections
        await self._broadcast_to_websockets(event)
        
        logger.info(f"Event delivered: {event.event_type} -> {delivered_count} subscribers")
    
    async def _broadcast_to_websockets(self, event: LiveEvent):
        """Broadcast event to all WebSocket connections."""
        if not self.websocket_connections:
            return
        
        message = {
            "type": "event",
            "event_id": event.event_id,
            "source_project_id": event.source_project_id,
            "event_type": event.event_type,
            "event_data": event.event_data,
            "timestamp": event.timestamp.isoformat(),
            "created_by": event.created_by
        }
        
        message_str = json.dumps(message)
        dead_connections = set()
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                dead_connections.add(websocket)
        
        # Remove dead connections
        self.websocket_connections -= dead_connections
    
    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent event history."""
        # Return recent events from queue (in real implementation, this would be from persistent storage)
        recent_events = self.event_queue[-limit:]
        return [
            {
                "event_id": event.event_id,
                "source_project_id": event.source_project_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "created_by": event.created_by
            }
            for event in recent_events
        ]


# Global event bus instance
_event_bus = None

def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus():
    """Reset the event bus (for testing)."""
    global _event_bus
    _event_bus = EventBus()
