"""REST API endpoints for room management."""
from fastapi import APIRouter, HTTPException
from typing import List
from src.rooms.models import (
    CreateRoomRequest,
    JoinRoomRequest,
    RoomResponse,
    PublicRoom,
    Player,
    RoomSettings,
    RoomPhase
)
from src.rooms.redis_manager import RoomManager
import secrets

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("/", response_model=RoomResponse)
async def create_room(request: CreateRoomRequest):
    """Create a new game room."""
    try:
        # Create host player
        player_id = secrets.token_urlsafe(8)
        host_player = Player(
            id=player_id,
            username=request.username,
            is_host=True,
            is_ready=True
        )
        
        # Create room settings
        settings = RoomSettings(
            max_players=request.max_players,
            category_id=request.category_id,
            is_public=request.is_public,
            password=request.password
        )
        
        # Create room
        room = await RoomManager.create_room(settings, host_player)
        
        return RoomResponse(
            id=room.id,
            host_id=room.host_id,
            phase=room.phase.value,
            player_count=len(room.players),
            max_players=room.settings.max_players,
            is_public=room.settings.is_public,
            has_password=bool(room.settings.password)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/public", response_model=List[PublicRoom])
async def get_public_rooms():
    """Get list of public rooms in waiting phase."""
    try:
        rooms = await RoomManager.get_public_rooms()
        return rooms
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{room_id}")
async def get_room(room_id: str):
    """Get full room state by ID."""
    try:
        room = await RoomManager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Return full room state as dict
        return room.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{room_id}/join")
async def join_room_rest(room_id: str, request: JoinRoomRequest):
    """
    REST endpoint to validate room join before WebSocket connection.
    Returns player_id if successful.
    """
    try:
        room = await RoomManager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Check password
        if room.settings.password and room.settings.password != request.password:
            raise HTTPException(status_code=403, detail="Invalid password")
        
        # Check capacity
        if len(room.players) >= room.settings.max_players:
            raise HTTPException(status_code=400, detail="Room is full")
        
        # Check if already in game
        if room.phase != RoomPhase.WAITING:
            raise HTTPException(status_code=400, detail="Game already started")
        
        # Generate player_id for WebSocket connection
        player_id = secrets.token_urlsafe(8)
        
        return {
            "room_id": room_id,
            "player_id": player_id,
            "message": "Ready to join via WebSocket"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
