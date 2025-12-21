"""Connection-related Socket.IO event handlers."""
import json
from typing import Dict

from src.sockets.server import sio
from src.redis.client import redis_client
from src.logging_config import get_logger

logger = get_logger(__name__)

# Store session data: sid -> {player_id, room_id, username}
# This is shared across all event modules
sessions: Dict[str, dict] = {}


@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    logger.info(f"🔌 Client connected: {sid}")
    await sio.emit('connected', {'sid': sid}, room=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    logger.info(f"🔌 Client disconnected: {sid}")
    
    # Import here to avoid circular dependency
    from src.sockets.room_events import handle_leave_room_internal
    
    # Auto leave room on disconnect
    if sid in sessions:
        session = sessions[sid]
        room_id = session.get('room_id')
        player_id = session.get('player_id')
        username = session.get('username')
        
        if room_id and player_id:
            logger.info(f"🔌 Auto-leaving room {room_id} for disconnected player {username}")
            await handle_leave_room_internal(room_id, player_id, username)
        
        del sessions[sid]
        logger.debug(f"🔌 Session cleaned up for {username}")
    else:
        logger.debug(f"🔌 No session to clean up for sid={sid}")


async def publish_event(event_type: str, data: dict):
    """Publish event to Redis Pub/Sub for cross-instance sync."""
    try:
        redis = redis_client.client
        channel = f"pubsub:{event_type}"
        message = json.dumps(data)
        await redis.publish(channel, message)
    except Exception as e:
        logger.error(f"❌ Failed to publish event to Redis: {e}")
