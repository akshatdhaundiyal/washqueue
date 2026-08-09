import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
try:
    from app.websocket_manager import ws_manager
except ImportError:
    from ..websocket_manager import ws_manager


logger = logging.getLogger("washqueue-ws-router")
router = APIRouter(tags=["websocket"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time live machine state broadcasts over local LAN.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial connected handshake acknowledgment
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to WashQueue Local Edge WebSocket broadcast."
        })
        while True:
            # Keep socket alive and receive client pings/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
