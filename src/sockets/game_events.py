"""Game-related Socket.IO event handlers."""
import asyncio

from src.sockets.server import sio
from src.rooms.redis_manager import RoomManager
from src.rooms.models import RoomPhase
from src.logging_config import get_logger
from src.game.logic import (
    start_game as logic_start_game,
    transition_to_playing,
    request_voting,
    submit_vote,
    calculate_results,
    ROLE_REVEAL_DURATION,
    PLAYING_DURATION,
    VOTING_DURATION,
)
from src.sockets.connection_events import sessions, publish_event

logger = get_logger(__name__)


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
        await publish_event('game_event', {
            'room_id': room_id,
            **event_data
        })
        
        logger.info(f"📢 Game event '{event_type}' in room {room_id} from {player_id}")
        
    except Exception as e:
        logger.exception(f"❌ Error in game_event: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def start_game(sid, data):
    """
    Start the game (host only).
    
    Expected data:
    {
        "room_id": "abc123",
        "language": "es",  # optional, defaults to "es"
        "category_ids": [1, 2, 3],  # optional, overrides room settings
        "settings": {
            "detective_enabled": false,
            "joker_enabled": false,
            "voting_time": 60,
            "discussion_timer_enabled": false,
            "discussion_time": 300
        }
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
        
        # Update room settings from host's choices
        if 'category_ids' in data:
            room.settings.category_ids = data['category_ids']
        elif 'category_id' in data:
            # Backwards compatibility
            room.settings.category_ids = [data['category_id']]
        
        settings = data.get('settings', {})
        if settings:
            room.settings.detective_enabled = settings.get('detective_enabled', False)
            room.settings.joker_enabled = settings.get('joker_enabled', False)
            room.settings.voting_time = settings.get('voting_time', 60)
            room.settings.discussion_timer_enabled = settings.get('discussion_timer_enabled', False)
            room.settings.discussion_time = settings.get('discussion_time', 300)
        
        # Save updated settings before starting game
        await RoomManager.update_room(room)
        
        # Start game
        language = data.get('language', 'es')
        room = await logic_start_game(room, language)
        
        if not room:
            await sio.emit('error', {'message': 'Failed to start game'}, room=sid)
            return
        
        logger.info(f"🎮 Game started in room {room_id} with detective={room.settings.detective_enabled}, joker={room.settings.joker_enabled}")
        
        # Send personalized room state to each player (with their role/word)
        await broadcast_personalized_game_state(room)
        
        # Schedule transition to PLAYING phase after ROLE_REVEAL_DURATION
        asyncio.create_task(schedule_phase_transition(room_id, RoomPhase.PLAYING, ROLE_REVEAL_DURATION))
        
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
        await broadcast_personalized_game_state(room)
        
        if should_start_voting:
            logger.info(f"🗳️ Voting phase started in room {room_id}")
            # Schedule voting timeout
            asyncio.create_task(schedule_phase_transition(room_id, RoomPhase.RESULTS, VOTING_DURATION))
        
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
            await broadcast_personalized_game_state(room)
            logger.info(f"🎉 Game ended in room {room_id}: {room.game_state.result}")
        
    except Exception as e:
        logger.exception(f"❌ Error in vote: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


async def broadcast_personalized_game_state(room):
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


async def schedule_phase_transition(room_id: str, next_phase: RoomPhase, delay: int):
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
        await broadcast_personalized_game_state(room)
        logger.info(f"🎮 Room {room_id} auto-transitioned to PLAYING phase")
        
        # Schedule voting phase timeout (5 minutes)
        asyncio.create_task(schedule_phase_transition(room_id, RoomPhase.VOTING, PLAYING_DURATION))
        
    elif next_phase == RoomPhase.VOTING and room.phase == RoomPhase.PLAYING:
        # Time's up - force voting phase
        room.phase = RoomPhase.VOTING
        if room.game_state:
            import time
            room.game_state.phase_start_time = time.time()
        await RoomManager.update_room(room)
        await broadcast_personalized_game_state(room)
        logger.info(f"⏰ Room {room_id} time's up - forced VOTING phase")
        
        # Schedule voting timeout
        asyncio.create_task(schedule_phase_transition(room_id, RoomPhase.RESULTS, VOTING_DURATION))
        
    elif next_phase == RoomPhase.RESULTS and room.phase == RoomPhase.VOTING:
        # Voting time's up - calculate results
        room = await calculate_results(room)
        await broadcast_personalized_game_state(room)
        logger.info(f"⏰ Room {room_id} voting time's up - showing results")
