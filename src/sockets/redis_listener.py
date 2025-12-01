"""Redis Pub/Sub listener for cross-instance event synchronization."""
import json
import asyncio
from src.redis.client import redis_client
from src.sockets.server import sio
from src.logging_config import get_logger


logger = get_logger(__name__)


async def redis_listener():
    """
    Listen to Redis Pub/Sub channels and broadcast events to Socket.IO clients.
    This enables multiple backend instances to stay in sync.
    """
    logger.info("🎧 Starting Redis Pub/Sub listener...")
    
    try:
        pubsub = await redis_client.pubsub()
        
        # Subscribe to all pubsub:* channels
        await pubsub.psubscribe("pubsub:*")
        
        logger.info("✅ Subscribed to pubsub:* channels")
        
        async for message in pubsub.listen():
            if message['type'] == 'pmessage':
                try:
                    # Parse channel and data
                    channel = message['channel']
                    event_type = channel.split(':', 1)[1] if ':' in channel else 'unknown'
                    data = json.loads(message['data'])
                    
                    # Get room_id from data
                    room_id = data.get('room_id')
                    
                    if not room_id:
                        continue
                    
                    # Broadcast to Socket.IO room based on event type
                    if event_type == 'player_joined':
                        await sio.emit('player_joined', {
                            'player_id': data['player_id'],
                            'username': data['username']
                        }, room=room_id)
                    
                    elif event_type == 'player_left':
                        await sio.emit('player_left', {
                            'player_id': data['player_id'],
                            'username': data['username']
                        }, room=room_id)
                    
                    elif event_type == 'game_event':
                        await sio.emit('game_event', {
                            'event_type': data['event_type'],
                            'player_id': data['player_id'],
                            'payload': data['payload']
                        }, room=room_id)
                    
                    logger.debug(f"📡 Broadcast Redis event '{event_type}' to room {room_id}")
                    
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Failed to parse Redis message: {message['data']}")
                except Exception as e:
                    logger.error(f"❌ Error processing Redis message: {e}")
    
    except Exception as e:
        logger.error(f"❌ Redis listener error: {e}")
        # Retry connection after delay
        await asyncio.sleep(5)
        asyncio.create_task(redis_listener())
