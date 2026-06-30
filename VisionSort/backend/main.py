import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging

from backend.database import db
from backend.mock_streamer import conveyor

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VisionSortAPI")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Initializing VisionSort application services...")
    await db.initialize()
    conveyor.start()
    yield
    # Shutdown tasks
    logger.info("Shutting down VisionSort application services...")
    conveyor.stop()

app = FastAPI(
    title="VisionSort Industrial Control API",
    description="Backend API managing conveyor stream, CNN inference, and MongoDB telemetry.",
    version="1.0.0",
    lifespan=lifespan
)

from fastapi import Request
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Active WebSocket connections
active_connections: list[WebSocket] = []

async def broadcast_conveyor_frame(frame_data: dict):
    """Callback function injected into the conveyor streamer to broadcast data."""
    if not active_connections:
        return
        
    # Create broadcast message
    message = {
        "type": "frame_update",
        "data": frame_data
    }
    
    # Broadcast to all connected WebSockets
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
            
    # Clean up disconnected sockets
    for ws in disconnected:
        if ws in active_connections:
            active_connections.remove(ws)

# Register the callback
conveyor.broadcast_callback = broadcast_conveyor_frame

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket client connected. Active: {len(active_connections)}")
    
    # Send initial configuration details
    await websocket.send_json({
        "type": "init_config",
        "data": {
            "target_material": conveyor.target_material,
            "speed": conveyor.speed_multiplier,
            "diverter_type": conveyor.diverter_type,
            "bypass_mode": conveyor.bypass_mode,
            "db_status": db.get_status_label()
        }
    })
    
    try:
        while True:
            # Wait for any control commands from the client
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "set_speed":
                speed = float(data.get("speed", 1.0))
                conveyor.set_speed(speed)
                # Broadcast updated config
                await broadcast_conveyor_frame(conveyor._render_frame())
                
            elif msg_type == "set_target":
                target = str(data.get("material", "Plastic"))
                conveyor.set_target_material(target)
                await broadcast_conveyor_frame(conveyor._render_frame())
                
            elif msg_type == "set_diverter_type":
                div_type = str(data.get("diverter_type", "Air Jet"))
                conveyor.set_diverter_type(div_type)
                await broadcast_conveyor_frame(conveyor._render_frame())
                
            elif msg_type == "set_bypass_mode":
                active = bool(data.get("bypass_mode", False))
                conveyor.set_bypass_mode(active)
                await broadcast_conveyor_frame(conveyor._render_frame())
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.info(f"Active connections remaining: {len(active_connections)}")

@app.get("/api/trends")
async def get_db_trends(limit: int = 12):
    """Endpoint to fetch historical volume and fault statistics from database."""
    try:
        trends = await db.get_hourly_trends(limit=limit)
        return JSONResponse(content={"status": "success", "data": trends})
    except Exception as e:
        logger.error(f"Error fetching trends API: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

# Mount the static files (frontend client)
# Ensure the frontend folder exists, otherwise FastAPI might complain on startup.
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
