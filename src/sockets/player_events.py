"""Player-related Socket.IO event handlers."""
from src.sockets.server import sio
from src.rooms.redis_manager import RoomManager
from src.logging_config import get_logger
from src.sockets.connection_events import sessions, publish_event

logger = get_logger(__name__)


@sio.event
async def update_username(sid, data):
    """
    Update player username in room.
    
    Expected data:
    {
        "room_id": "abc123",
        "new_username": "NewName"
    }
    """
    try:
        logger.debug(f"✏️ update_username event from sid={sid}")
        
        if sid not in sessions:
            await sio.emit('error', {'message': 'No session found'}, room=sid)
            return
        
        session = sessions[sid]
        room_id = session.get('room_id')
        player_id = session.get('player_id')
        old_username = session.get('username')
        new_username = data.get('new_username', '').strip()
        
        if not new_username:
            await sio.emit('error', {'message': 'Username cannot be empty'}, room=sid)
            return
        
        if len(new_username) > 20:
            await sio.emit('error', {'message': 'Username too long (max 20 characters)'}, room=sid)
            return
        
        if not room_id or not player_id:
            await sio.emit('error', {'message': 'Not in a room'}, room=sid)
            return
        
        # Update username in Redis
        room = await RoomManager.update_player_username(room_id, player_id, new_username)
        
        if not room:
            await sio.emit('error', {'message': 'Failed to update username'}, room=sid)
            return
        
        # Update session
        sessions[sid]['username'] = new_username
        
        logger.info(f"✏️ {old_username} changed username to {new_username} in room {room_id}")
        
        # Broadcast updated room state to all players
        await sio.emit('room_state', room.dict(), room=room_id)
        
        # Also emit specific event for username change
        await sio.emit('username_changed', {
            'player_id': player_id,
            'old_username': old_username,
            'new_username': new_username
        }, room=room_id)
        
        # Publish to Redis for cross-instance sync
        await publish_event('username_changed', {
            'room_id': room_id,
            'player_id': player_id,
            'old_username': old_username,
            'new_username': new_username
        })
        
    except Exception as e:
        logger.exception(f"❌ Error in update_username: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def toggle_ready(sid, data):
    """
    Toggle player ready status.
    
    Expected data:
    {
        "room_id": "abc123"
    }
    """
    try:
        logger.debug(f"✅ toggle_ready event from sid={sid}")
        
        if sid not in sessions:
            await sio.emit('error', {'message': 'No session found'}, room=sid)
            return
        
        session = sessions[sid]
        room_id = session.get('room_id')
        player_id = session.get('player_id')
        username = session.get('username')
        
        if not room_id or not player_id:
            await sio.emit('error', {'message': 'Not in a room'}, room=sid)
            return
        
        # Get current room state
        room = await RoomManager.get_room(room_id)
        if not room:
            await sio.emit('error', {'message': 'Room not found'}, room=sid)
            return
        
        if player_id not in room.players:
            await sio.emit('error', {'message': 'Player not in room'}, room=sid)
            return
        
        # Toggle ready status
        current_ready = room.players[player_id].is_ready
        new_ready = not current_ready
        
        # Update in Redis
        room = await RoomManager.update_player(room_id, player_id, is_ready=new_ready)
        
        if not room:
            await sio.emit('error', {'message': 'Failed to update ready status'}, room=sid)
            return
        
        logger.info(f"{'✅' if new_ready else '⏸️'} {username} is now {'ready' if new_ready else 'not ready'} in room {room_id}")
        
        # Broadcast updated room state to all players
        await sio.emit('room_state', room.dict(), room=room_id)
        
        # Also emit specific event for ready change
        await sio.emit('player_ready_changed', {
            'player_id': player_id,
            'username': username,
            'is_ready': new_ready
        }, room=room_id)
        
        # Publish to Redis for cross-instance sync
        await publish_event('player_ready_changed', {
            'room_id': room_id,
            'player_id': player_id,
            'username': username,
            'is_ready': new_ready
        })
        
    except Exception as e:
        logger.exception(f"❌ Error in toggle_ready: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


async def broadcast_player_joined(room_id: str, player_id: str, username: str):
    """Broadcast player_joined event to room."""
    await sio.emit('player_joined', {
        'player_id': player_id,
        'username': username
    }, room=room_id)


async def broadcast_player_left(room_id: str, player_id: str, username: str):
    """Broadcast player_left event to room."""
    await sio.emit('player_left', {
        'player_id': player_id,
        'username': username
    }, room=room_id)
