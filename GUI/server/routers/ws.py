# routers/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.pipeline_stub import register_connection, unregister_connection

router = APIRouter(tags=["WebSocket Pipeline Streaming"])


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    await register_connection(user_id, websocket)
    try:
        while True:
            # Keep connection open, receive any client heartbeats
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await unregister_connection(user_id)
    except Exception:
        await unregister_connection(user_id)
