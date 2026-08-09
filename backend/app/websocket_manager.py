import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("washqueue-websocket")

class ConnectionManager:
    """
    Manages active WebSocket client connections on the local hostel network
    and broadcasts real-time machine updates to all connected dashboards.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcasts a JSON message to all connected local WebSocket clients.
        """
        if not self.active_connections:
            return

        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message to a client: {e}")
                disconnected_clients.append(connection)

        # Cleanup stale connections
        for dead_client in disconnected_clients:
            self.disconnect(dead_client)

ws_manager = ConnectionManager()
