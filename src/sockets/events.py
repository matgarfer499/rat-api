"""Socket.IO event handlers."""
import json
import asyncio
from typing import Dict
import secrets

from src.sockets.server import sio
from src.rooms.redis_manager import RoomManager
from src.rooms.models import Player, RoomPhase
from src.redis.client import redis_client
from src.logging_config import get_logger
from src.game.logic import (
    start_game as logic_start_game,
    transition_to_playing,
    request_voting,
    submit_vote,
    calculate_results,
    return_to_lobby,
    ROLE_REVEAL_DURATION,
    PLAYING_DURATION,
    VOTING_DURATION,
)


logger = get_logger(__name__)

# Store session data: sid -> {player_id, room_id, username}
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
    
    # Auto leave room on disconnect
    if sid in sessions:
        session = sessions[sid]
        room_id = session.get('room_id')
        player_id = session.get('player_id')
        username = session.get('username')
        
        if room_id and player_id:
            logger.info(f"🔌 Auto-leaving room {room_id} for disconnected player {username}")
            await _handle_leave_room(room_id, player_id, username)
        
        del sessions[sid]
        logger.debug(f"🔌 Session cleaned up for {username}")
    else:
        logger.debug(f"🔌 No session to clean up for sid={sid}")


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
        await _publish_event('player_joined', {
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
        
        await _handle_leave_room(room_id, player_id, username)
        
        # Leave Socket.IO room
        await sio.leave_room(sid, room_id)
        
        # Clear session
        del sessions[sid]
        
        await sio.emit('left_room', {'room_id': room_id}, room=sid)
        logger.info(f"✅ {username} successfully left room {room_id}")
        
    except Exception as e:
        logger.exception(f"❌ Error in leave_room: {e}")


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
        await _publish_event('username_changed', {
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
        await _publish_event('player_ready_changed', {
            'room_id': room_id,
            'player_id': player_id,
            'username': username,
            'is_ready': new_ready
        })
        
    except Exception as e:
        logger.exception(f"❌ Error in toggle_ready: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def game_event(sid, data):
    """
    Broadcast a game event to the room.
    
    Expected data:
    {
        "room_id": "abc123",
        "event_type": "hint_submitted" | "vote_submitted" | "ready_toggle" | etc,
        "payload": { ... }
    }
    """
    try:
        room_id = data.get('room_id')
        event_type = data.get('event_type')
        payload = data.get('payload', {})
        
        if not room_id or not event_type:
            await sio.emit('error', {'message': 'room_id and event_type required'}, room=sid)
            return
        
        # Verify player is in room
        if sid not in sessions or sessions[sid].get('room_id') != room_id:
            await sio.emit('error', {'message': 'Not in this room'}, room=sid)
            return
        
        player_id = sessions[sid]['player_id']
        
        # Broadcast to room
        event_data = {
            'event_type': event_type,
            'player_id': player_id,
            'payload': payload
        }
        
        await sio.emit('game_event', event_data, room=room_id)
        
        # Publish to Redis for cross-instance sync
        await _publish_event('game_event', {
            'room_id': room_id,
            **event_data
        })
        
        logger.info(f"📢 Game event '{event_type}' in room {room_id} from {player_id}")
        
    except Exception as e:
        logger.exception(f"❌ Error in game_event: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


# Helper functions
async def _handle_leave_room(room_id: str, player_id: str, username: str):
    """Handle player leaving room."""
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
        await _publish_event('room_closed', {
            'room_id': room_id,
            'reason': reason
        })
    else:
        # Room still exists - notify remaining players
        logger.info(f"👋 {username} left room {room_id} - {len(room_after.players)} players remaining")
        
        # Notify about player leaving
        await _broadcast_player_left(room_id, player_id, username)
        
        # Send updated room state to all remaining players
        await sio.emit('room_state', room_after.dict(), room=room_id)
        
        # Publish to Redis
        await _publish_event('player_left', {
            'room_id': room_id,
            'player_id': player_id,
            'username': username,
            'remaining_players': len(room_after.players)
        })


async def _broadcast_player_joined(room_id: str, player_id: str, username: str):
    """Broadcast player_joined event to room."""
    await sio.emit('player_joined', {
        'player_id': player_id,
        'username': username
    }, room=room_id)


async def _broadcast_player_left(room_id: str, player_id: str, username: str):
    """Broadcast player_left event to room."""
    await sio.emit('player_left', {
        'player_id': player_id,
        'username': username
    }, room=room_id)


async def _publish_event(event_type: str, data: dict):
    """Publish event to Redis Pub/Sub for cross-instance sync."""
    try:
        redis = redis_client.client
        channel = f"pubsub:{event_type}"
        message = json.dumps(data)
        await redis.publish(channel, message)
    except Exception as e:
        logger.error(f"❌ Failed to publish event to Redis: {e}")


# ============================================
# GAME EVENTS
# ============================================

@sio.event
async def start_game(sid, data):
    """
    Start the game (host only).
    
    Expected data:
    {
        "room_id": "abc123",
        "language": "es"  # optional, defaults to "es"
    }
    """
    try:
        logger.debug(f"🎮 start_game event from sid={sid}")
        
        if sid not in sessions:
            await sio.emit('error', {'message': 'No session found'}, room=sid)
            return
        
        session = sessions[sid]
        room_id = session.get('room_id')
        player_id = session.get('player_id')
        
        if not room_id:
            await sio.emit('error', {'message': 'Not in a room'}, room=sid)
            return
        
        # Get room
        room = await RoomManager.get_room(room_id)
        if not room:
            await sio.emit('error', {'message': 'Room not found'}, room=sid)
            return
        
        # Only host can start
        if player_id != room.host_id:
            await sio.emit('error', {'message': 'Only the host can start the game'}, room=sid)
            return
        
        # Check all players are ready
        players_list = list(room.players.values())
        if len(players_list) < 3:
            await sio.emit('error', {'message': 'Need at least 3 players to start'}, room=sid)
            return
        
        all_ready = all(p.is_ready for p in players_list)
        if not all_ready:
            await sio.emit('error', {'message': 'All players must be ready'}, room=sid)
            return
        
        # Start game
        language = data.get('language', 'es')
        room = await logic_start_game(room, language)
        
        if not room:
            await sio.emit('error', {'message': 'Failed to start game'}, room=sid)
            return
        
        logger.info(f"🎮 Game started in room {room_id}")
        
        # Send personalized room state to each player (with their role/word)
        await _broadcast_personalized_game_state(room)
        
        # Schedule transition to PLAYING phase after ROLE_REVEAL_DURATION
        asyncio.create_task(_schedule_phase_transition(room_id, RoomPhase.PLAYING, ROLE_REVEAL_DURATION))
        
    except Exception as e:
        logger.exception(f"❌ Error in start_game: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def request_vote(sid, data):
    """
    Request to start voting phase.
    
    Expected data:
    {
        "room_id": "abc123"
    }
    """
    try:
        logger.debug(f"🗳️ request_vote event from sid={sid}")
        
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
        
        if room.phase != RoomPhase.PLAYING:
            await sio.emit('error', {'message': 'Can only request vote during playing phase'}, room=sid)
            return
        
        room, should_start_voting = await request_voting(room, player_id)
        
        # Broadcast updated state
        await _broadcast_personalized_game_state(room)
        
        if should_start_voting:
            logger.info(f"🗳️ Voting phase started in room {room_id}")
            # Schedule voting timeout
            asyncio.create_task(_schedule_phase_transition(room_id, RoomPhase.RESULTS, VOTING_DURATION))
        
    except Exception as e:
        logger.exception(f"❌ Error in request_vote: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event 
async def vote(sid, data):
    """
    Submit a vote.
    
    Expected data:
    {
        "room_id": "abc123",
        "voted_for_id": "player_id"
    }
    """
    try:
        logger.debug(f"🗳️ vote event from sid={sid}")
        
        if sid not in sessions:
            await sio.emit('error', {'message': 'No session found'}, room=sid)
            return
        
        session = sessions[sid]
        room_id = session.get('room_id')
        voter_id = session.get('player_id')
        voted_for_id = data.get('voted_for_id')
        
        if not room_id or not voted_for_id:
            await sio.emit('error', {'message': 'room_id and voted_for_id required'}, room=sid)
            return
        
        room = await RoomManager.get_room(room_id)
        if not room:
            await sio.emit('error', {'message': 'Room not found'}, room=sid)
            return
        
        if room.phase != RoomPhase.VOTING:
            await sio.emit('error', {'message': 'Can only vote during voting phase'}, room=sid)
            return
        
        room, all_voted = await submit_vote(room, voter_id, voted_for_id)
        
        # Broadcast vote count update
        await sio.emit('vote_update', {
            'votes_submitted': room.game_state.votes_submitted,
            'total_players': len(room.players)
        }, room=room_id)
        
        if all_voted:
            # All votes in - calculate results immediately
            room = await calculate_results(room)
            await _broadcast_personalized_game_state(room)
            logger.info(f"🎉 Game ended in room {room_id}: {room.game_state.result}")
        
    except Exception as e:
        logger.exception(f"❌ Error in vote: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


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
        
        room = await return_to_lobby(room)
        
        # Broadcast room state
        await sio.emit('room_state', room.dict(), room=room_id)
        
        logger.info(f"🏠 Room {room_id} returned to lobby")
        
    except Exception as e:
        logger.exception(f"❌ Error in back_to_lobby: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


# ============================================
# GAME HELPER FUNCTIONS
# ============================================

async def _broadcast_personalized_game_state(room):
    """
    Send personalized room state to each player.
    Each player only sees their own role and word.
    """
    room_dict = room.dict()
    
    # For each connected player, send personalized state
    for sid, session in sessions.items():
        if session.get('room_id') != room.id:
            continue
        
        player_id = session.get('player_id')
        if player_id not in room.players:
            continue
        
        # Create personalized room dict
        personalized = room_dict.copy()
        personalized['players'] = {}
        
        for pid, player in room.players.items():
            player_dict = player.dict()
            
            # Only include role and word for the current player
            if pid != player_id:
                player_dict['role'] = None
                player_dict['word'] = None
            
            personalized['players'][pid] = player_dict
        
        # Don't reveal impostor_id in game_state during play
        if personalized.get('game_state') and room.phase != RoomPhase.RESULTS:
            personalized['game_state']['impostor_id'] = None
        
        await sio.emit('room_state', personalized, room=sid)


async def _schedule_phase_transition(room_id: str, next_phase: RoomPhase, delay: int):
    """
    Schedule a phase transition after a delay.
    This handles automatic phase changes (role reveal -> playing, voting timeout -> results).
    """
    await asyncio.sleep(delay)
    
    room = await RoomManager.get_room(room_id)
    if not room:
        return
    
    # Check if transition is still valid
    if next_phase == RoomPhase.PLAYING and room.phase == RoomPhase.ROLE_REVEAL:
        room = await transition_to_playing(room)
        await _broadcast_personalized_game_state(room)
        logger.info(f"🎮 Room {room_id} auto-transitioned to PLAYING phase")
        
        # Schedule voting phase timeout (5 minutes)
        asyncio.create_task(_schedule_phase_transition(room_id, RoomPhase.VOTING, PLAYING_DURATION))
        
    elif next_phase == RoomPhase.VOTING and room.phase == RoomPhase.PLAYING:
        # Time's up - force voting phase
        room.phase = RoomPhase.VOTING
        if room.game_state:
            import time
            room.game_state.phase_start_time = time.time()
        await RoomManager.update_room(room)
        await _broadcast_personalized_game_state(room)
        logger.info(f"⏰ Room {room_id} time's up - forced VOTING phase")
        
        # Schedule voting timeout
        asyncio.create_task(_schedule_phase_transition(room_id, RoomPhase.RESULTS, VOTING_DURATION))
        
    elif next_phase == RoomPhase.RESULTS and room.phase == RoomPhase.VOTING:
        # Voting time's up - calculate results
        room = await calculate_results(room)
        await _broadcast_personalized_game_state(room)
        logger.info(f"⏰ Room {room_id} voting time's up - showing results")
