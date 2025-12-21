"""Room-related Socket.IO event handlers."""
import secrets

from src.sockets.server import sio
from src.rooms.redis_manager import RoomManager
from src.rooms.models import Player, RoomPhase
from src.logging_config import get_logger
from src.game.logic import return_to_lobby as logic_return_to_lobby
from src.sockets.connection_events import sessions, publish_event
from src.sockets.player_events import broadcast_player_left

logger = get_logger(__name__)


@sio.event
async def join_room(sid, data):
    """
    Join a room.
    
    Expected data:
    {
        "room_id": "abc123",
        "username": "Player1",
        "password": "optional"
    }
    """
    logger.debug(f"🔍 join_room called - sid={sid}, data={data}")
    
    try:
        room_id = data.get('room_id')
        username = data.get('username')
        password = data.get('password')
        
        logger.debug(f"🔍 Parsed: room_id={room_id}, username={username}")
        
        if not room_id or not username:
            await sio.emit('error', {'message': 'room_id and username required'}, room=sid)
            return
        
        # Get room
        logger.debug(f"🔍 Getting room {room_id}...")
        room = await RoomManager.get_room(room_id)
        if not room:
            logger.warning(f"❌ Room {room_id} not found")
            await sio.emit('error', {'message': 'Room not found'}, room=sid)
            return
        
        logger.debug(f"🔍 Room found: {room.id}, current players: {len(room.players)}")
        
        # Check if player is already in room (host or reconnecting)
        existing_player = None
        for pid, p in room.players.items():
            if p.username == username:
                existing_player = (pid, p)
                logger.debug(f"🔍 Found existing player: {pid} ({username})")
                break
        
        # Only check password for NEW players (not host or reconnecting players)
        if not existing_player:
            if room.settings.password and room.settings.password != password:
                logger.warning(f"❌ Invalid password for room {room_id}")
                await sio.emit('error', {'message': 'Invalid password'}, room=sid)
                return
        
        if existing_player:
            # Player already exists - just reconnect
            player_id, player = existing_player
            logger.info(f"🔄 Reconnecting existing player {username} ({player_id})")
        else:
            # Check room capacity for new players
            if len(room.players) >= room.settings.max_players:
                await sio.emit('error', {'message': 'Room is full'}, room=sid)
                return
            
            # Create new player
            player_id = secrets.token_urlsafe(8)
            player = Player(
                id=player_id,
                username=username,
                is_host=False
            )
            
            logger.debug(f"🔍 Created new player {player_id} for {username}")
            
            # Add player to room
            await RoomManager.add_player(room_id, player)
            logger.debug(f"🔍 Player added to room successfully")
        
        # Join Socket.IO room FIRST (before any broadcasts)
        await sio.enter_room(sid, room_id)
        logger.debug(f"🔍 Player {player_id} entered Socket.IO room {room_id}")
        
        # Store session
        sessions[sid] = {
            'player_id': player_id,
            'room_id': room_id,
            'username': username
        }
        
        # Get updated room state from Redis
        updated_room = await RoomManager.get_room(room_id)
        if updated_room:
            # Broadcast to ALL players in room (including the new one)
            logger.debug(f"📤 Broadcasting room_state to entire room {room_id}: {len(updated_room.players)} players")
            await sio.emit('room_state', updated_room.dict(), room=room_id)
        else:
            logger.warning(f"⚠️ Could not get updated room {room_id}")
        
        # Publish to Redis for cross-instance sync
        await publish_event('player_joined', {
            'room_id': room_id,
            'player_id': player_id,
            'username': username
        })
        
        logger.info(f"✅ {username} joined room {room_id}")
        
    except Exception as e:
        logger.exception(f"❌ Error in join_room: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def leave_room(sid, data):
    """
    Leave a room.
    
    Expected data:
    {
        "room_id": "abc123"
    }
    """
    try:
        logger.debug(f"🚪 leave_room event from sid={sid}")
        
        if sid not in sessions:
            logger.warning(f"⚠️ No session found for sid={sid}")
            return
        
        session = sessions[sid]
        room_id = session.get('room_id')
        player_id = session.get('player_id')
        username = session.get('username')
        
        if not room_id or not player_id:
            logger.warning(f"⚠️ Incomplete session data for sid={sid}")
            return
        
        logger.info(f"🚪 {username} ({player_id}) leaving room {room_id}")
        
        await handle_leave_room_internal(room_id, player_id, username)
        
        # Leave Socket.IO room
        await sio.leave_room(sid, room_id)
        
        # Clear session
        del sessions[sid]
        
        await sio.emit('left_room', {'room_id': room_id}, room=sid)
        logger.info(f"✅ {username} successfully left room {room_id}")
        
    except Exception as e:
        logger.exception(f"❌ Error in leave_room: {e}")


@sio.event
async def back_to_lobby(sid, data):
    """
    Return to lobby after game ends (host only).
    
    Expected data:
    {
        "room_id": "abc123"
    }
    """
    try:
        logger.debug(f"🏠 back_to_lobby event from sid={sid}")
        
        if sid not in sessions:
            await sio.emit('error', {'message': 'No session found'}, room=sid)
            return
        
        session = sessions[sid]
        room_id = session.get('room_id')
        player_id = session.get('player_id')
        
        if not room_id:
            await sio.emit('error', {'message': 'Not in a room'}, room=sid)
            return
        
        room = await RoomManager.get_room(room_id)
        if not room:
            await sio.emit('error', {'message': 'Room not found'}, room=sid)
            return
        
        # Only host can return to lobby
        if player_id != room.host_id:
            await sio.emit('error', {'message': 'Only the host can return to lobby'}, room=sid)
            return
        
        if room.phase != RoomPhase.RESULTS:
            await sio.emit('error', {'message': 'Can only return to lobby from results phase'}, room=sid)
            return
        
        room = await logic_return_to_lobby(room)
        
        # Broadcast room state
        await sio.emit('room_state', room.dict(), room=room_id)
        
        logger.info(f"🏠 Room {room_id} returned to lobby")
        
    except Exception as e:
        logger.exception(f"❌ Error in back_to_lobby: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


async def handle_leave_room_internal(room_id: str, player_id: str, username: str):
    """Handle player leaving room (internal function)."""
    logger.debug(f"🚪 Processing leave_room: {username} ({player_id}) from room {room_id}")
    
    # Get room before removing player to check player count
    room_before = await RoomManager.get_room(room_id)
    if not room_before:
        logger.warning(f"⚠️ Room {room_id} not found, nothing to do")
        return
    
    was_host = player_id == room_before.host_id
    player_count_before = len(room_before.players)
    
    # Remove player from room
    room_after = await RoomManager.remove_player(room_id, player_id)
    
    if room_after is None:
        # Room was deleted (either empty or host left)
        reason = 'host_left' if was_host else 'room_empty'
        if player_count_before <= 1:
            logger.info(f"🗑️ Room {room_id} deleted - last player left")
        elif was_host:
            logger.info(f"🗑️ Room {room_id} deleted - host left")
        
        # Notify all remaining players that room was closed
        await sio.emit('room_closed', {
            'room_id': room_id,
            'reason': reason
        }, room=room_id)
        
        # Publish to Redis
        await publish_event('room_closed', {
            'room_id': room_id,
            'reason': reason
        })
    else:
        # Room still exists - notify remaining players
        logger.info(f"👋 {username} left room {room_id} - {len(room_after.players)} players remaining")
        
        # Notify about player leaving
        await broadcast_player_left(room_id, player_id, username)
        
        # Send updated room state to all remaining players
        await sio.emit('room_state', room_after.dict(), room=room_id)
        
        # Publish to Redis
        await publish_event('player_left', {
            'room_id': room_id,
            'player_id': player_id,
            'username': username,
            'remaining_players': len(room_after.players)
        })
