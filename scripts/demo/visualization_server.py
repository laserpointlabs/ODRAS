#!/usr/bin/env python3
"""
Visualization Server with WebSocket Support

Provides WebSocket server for real-time lattice visualization updates.
Serves static files and handles live event broadcasting.

Usage:
    python scripts/demo/visualization_server.py [--port 8080]
"""

import asyncio
import json
import logging
import websockets
import http.server
import socketserver
import threading
import time
from pathlib import Path
from typing import Set, Dict, Any
import argparse
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"


class LatticeWebSocketServer:
    """WebSocket server for real-time lattice updates."""
    
    def __init__(self, port: int = 8081):
        self.port = port
        self.connections: Set[websockets.WebSocketServerProtocol] = set()
        self.lattice_state = {}
        self.event_history = []
        self.odras_client = None
        self.auth_token = None
    
    async def authenticate_with_odras(self) -> bool:
        """Authenticate with ODRAS API."""
        try:
            self.odras_client = httpx.AsyncClient(base_url=ODRAS_BASE_URL, timeout=30.0)
            response = await self.odras_client.post(
                "/api/auth/login",
                json={"username": USERNAME, "password": PASSWORD}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token") or data.get("token")
                if self.auth_token:
                    self.odras_client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                    logger.info("✅ Authenticated with ODRAS")
                    return True
            
            logger.error(f"❌ ODRAS authentication failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"❌ ODRAS authentication error: {e}")
            return False
    
    async def fetch_lattice_data(self) -> Dict[str, Any]:
        """Fetch current lattice data from ODRAS."""
        if not self.odras_client or not self.auth_token:
            return {"projects": [], "relationships": []}
        
        try:
            # Get all projects
            projects_response = await self.odras_client.get("/api/projects")
            projects = projects_response.json().get("projects", []) if projects_response.status_code == 200 else []
            
            # Get relationships for each project
            relationships = []
            for project in projects:
                project_id = project.get("project_id")
                if project_id:
                    rel_response = await self.odras_client.get(f"/api/projects/{project_id}/relationships")
                    if rel_response.status_code == 200:
                        project_rels = rel_response.json().get("relationships", [])
                        for rel in project_rels:
                            relationships.append({
                                "source_project_id": project_id,
                                "target_project_id": rel.get("target_project_id"),
                                "relationship_type": rel.get("relationship_type", "coordinates_with")
                            })
            
            return {"projects": projects, "relationships": relationships}
            
        except Exception as e:
            logger.error(f"Error fetching lattice data: {e}")
            return {"projects": [], "relationships": []}
    
    async def handle_websocket(self, websocket, path):
        """Handle WebSocket connections."""
        self.connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.connections)}")
        
        try:
            # Send initial lattice data
            try:
                lattice_data = await self.fetch_lattice_data()
                await websocket.send(json.dumps({
                    "type": "initial_lattice",
                    "data": lattice_data
                }))
                logger.info(f"Sent initial lattice data: {len(lattice_data.get('projects', []))} projects")
            except Exception as e:
                logger.error(f"Error fetching/sending initial data: {e}", exc_info=True)
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Failed to fetch lattice data: {str(e)}"
                }))
            
            # Keep connection alive and handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
        finally:
            self.connections.discard(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.connections)}")
    
    async def handle_message(self, websocket, data: Dict[str, Any]):
        """Handle incoming WebSocket messages."""
        message_type = data.get("type")
        
        if message_type == "request_lattice_update":
            # Send fresh lattice data
            lattice_data = await self.fetch_lattice_data()
            await websocket.send(json.dumps({
                "type": "lattice_update",
                "data": lattice_data
            }))
        
        elif message_type == "simulate_event":
            # Simulate an event for demonstration
            event_data = data.get("event_data", {})
            await self.simulate_event(event_data)
        
        elif message_type == "request_project_state":
            # Send project state information
            project_id = data.get("project_id")
            if project_id:
                state = await self.get_project_state(project_id)
                await websocket.send(json.dumps({
                    "type": "project_state",
                    "project_id": project_id,
                    "state": state
                }))
    
    async def simulate_event(self, event_data: Dict[str, Any]):
        """Simulate an event and broadcast to all connections."""
        event = {
            "type": "simulated_event",
            "event_id": f"sim_{int(time.time() * 1000)}",
            "source_project_id": event_data.get("source_project_id"),
            "event_type": event_data.get("event_type", "data.updated"),
            "event_data": event_data.get("payload", {}),
            "timestamp": time.time()
        }
        
        self.event_history.append(event)
        
        # Broadcast to all connections
        await self.broadcast_to_all(event)
        
        logger.info(f"Simulated event: {event['event_type']} from {event['source_project_id']}")
    
    async def get_project_state(self, project_id: str) -> Dict[str, Any]:
        """Get current state of a project."""
        # Mock project state (in real implementation, would query ODRAS)
        states = ["draft", "processing", "ready", "published"]
        import random
        return {
            "project_id": project_id,
            "state": random.choice(states),
            "progress": random.randint(0, 100),
            "last_updated": time.time()
        }
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients."""
        if not self.connections:
            return
        
        message_str = json.dumps(message)
        dead_connections = set()
        
        for websocket in self.connections:
            try:
                await websocket.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                dead_connections.add(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                dead_connections.add(websocket)
        
        # Remove dead connections
        self.connections -= dead_connections
        
        if dead_connections:
            logger.info(f"Removed {len(dead_connections)} dead connections")
    
    async def periodic_lattice_update(self):
        """Periodically fetch and broadcast lattice updates."""
        while True:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                if self.connections:
                    lattice_data = await self.fetch_lattice_data()
                    await self.broadcast_to_all({
                        "type": "lattice_update",
                        "data": lattice_data,
                        "timestamp": time.time()
                    })
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic update: {e}")
    
    async def start_server(self):
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on port {self.port}")
        
        # Try to authenticate with ODRAS
        await self.authenticate_with_odras()
        
        # Start WebSocket server
        # websockets.serve calls handler(websocket) - path is available on websocket.path
        async def handler(websocket):
            path = getattr(websocket, 'path', '')
            await self.handle_websocket(websocket, path)
        
        async with websockets.serve(handler, "localhost", self.port):
            logger.info(f"✅ WebSocket server running on ws://localhost:{self.port}")
            
            # Start periodic updates
            update_task = asyncio.create_task(self.periodic_lattice_update())
            
            try:
                await asyncio.Future()  # Run forever
            except KeyboardInterrupt:
                logger.info("Shutting down server...")
                update_task.cancel()


class StaticFileServer:
    """HTTP server for static files."""
    
    def __init__(self, port: int = 8080, static_dir: str = "scripts/demo/static"):
        self.port = port
        self.static_dir = Path(static_dir)
    
    def start_server(self):
        """Start HTTP server for static files."""
        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(self.static_dir), **kwargs)
        
        with socketserver.TCPServer(("", self.port), CustomHandler) as httpd:
            logger.info(f"✅ Static file server running on http://localhost:{self.port}")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                logger.info("Static file server shutting down...")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Start visualization server")
    parser.add_argument("--ws-port", type=int, default=8081, help="WebSocket port (default: 8081)")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP port for static files (default: 8080)")
    parser.add_argument("--websocket-only", action="store_true", help="Only start WebSocket server")
    args = parser.parse_args()
    
    if args.websocket_only:
        # Start only WebSocket server
        server = LatticeWebSocketServer(args.ws_port)
        asyncio.run(server.start_server())
    else:
        # Start both servers
        websocket_server = LatticeWebSocketServer(args.ws_port)
        static_server = StaticFileServer(args.http_port)
        
        # Start static server in thread
        static_thread = threading.Thread(target=static_server.start_server, daemon=True)
        static_thread.start()
        
        print(f"🌐 Open http://localhost:{args.http_port}/lattice_demo.html to view visualization")
        
        # Start WebSocket server
        asyncio.run(websocket_server.start_server())


if __name__ == "__main__":
    main()
