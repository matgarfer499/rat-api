"""Redis-based room state management."""
import json
import secrets
import time
from typing import Optional, List, Dict
from src.redis.client import redis_client
from src.rooms.models import Room, Player, RoomSettings, RoomPhase


class RoomManager:
    """Manages room state in Redis using HASH and SET data structures."""
    
    ROOM_PREFIX = "room:"
    ROOM_PLAYERS_PREFIX = "room:players:"
    PUBLIC_ROOMS_SET = "rooms:public"
    ROOM_TTL = 86400  # 24 hours
    
    @staticmethod
    def _generate_room_id() -> str:
        """Generate a unique room ID."""
        return secrets.token_urlsafe(8)
    
    @staticmethod
    async def create_room(settings: RoomSettings, host_player: Player) -> Room:
        """Create a new room with the host player."""
        room_id = RoomManager._generate_room_id()
        
        room = Room(
            id=room_id,
            host_id=host_player.id,
            settings=settings,
            phase=RoomPhase.WAITING,
            players={host_player.id: host_player},
            created_at=time.time()
        )
        
        await RoomManager._save_room(room)
        
        # Add to public rooms set if public
        if settings.is_public:
            await RoomManager._add_to_public_rooms(room_id, len(room.players))
        
        return room
    
    @staticmethod
    async def get_room(room_id: str) -> Optional[Room]:
        """Get room by ID (case-insensitive)."""
        redis = redis_client.client
        
        # Search for room with case-insensitive match
        # Try exact match first
        room_key = f"{RoomManager.ROOM_PREFIX}{room_id}"
        room_data = await redis.hgetall(room_key)
        
        # If not found, try to find by scanning all rooms
        if not room_data:
            keys = await redis.keys(f"{RoomManager.ROOM_PREFIX}*")
            for key in keys:
                key_id = key.replace(RoomManager.ROOM_PREFIX, "")
                if key_id.lower() == room_id.lower():
                    room_key = key
                    room_data = await redis.hgetall(room_key)
                    break
        
        if not room_data:
            return None
        
        # Get players - use the found room key's ID
        actual_room_id = room_key.replace(RoomManager.ROOM_PREFIX, "")
        players_key = f"{RoomManager.ROOM_PLAYERS_PREFIX}{actual_room_id}"
        players_data = await redis.hgetall(players_key)
        
        # Parse room
        players = {
            player_id: Player(**json.loads(player_json))
            for player_id, player_json in players_data.items()
        }
        
        room_dict = {
            "id": room_data["id"],
            "host_id": room_data["host_id"],
            "settings": json.loads(room_data["settings"]),
            "phase": room_data["phase"],
            "players": players,
            "word": room_data.get("word"),
            "round_number": int(room_data.get("round_number", 0)),
            "created_at": float(room_data["created_at"])
        }
        
        return Room(**room_dict)
    
    @staticmethod
    async def _save_room(room: Room):
        """Save room to Redis."""
        redis = redis_client.client
        
        room_key = f"{RoomManager.ROOM_PREFIX}{room.id}"
        players_key = f"{RoomManager.ROOM_PLAYERS_PREFIX}{room.id}"
        
        # Save room metadata
        room_data = {
            "id": room.id,
            "host_id": room.host_id,
            "settings": json.dumps(room.settings.dict()),
            "phase": room.phase.value,
            "word": room.word or "",
            "round_number": str(room.round_number),
            "created_at": str(room.created_at)
        }
        await redis.hset(room_key, mapping=room_data)
        await redis.expire(room_key, RoomManager.ROOM_TTL)
        
        # Save players
        if room.players:
            players_data = {
                player_id: json.dumps(player.dict())
                for player_id, player in room.players.items()
            }
            await redis.delete(players_key)  # Clear old players
            await redis.hset(players_key, mapping=players_data)
            await redis.expire(players_key, RoomManager.ROOM_TTL)
    
    @staticmethod
    async def update_room(room: Room):
        """Update existing room."""
        await RoomManager._save_room(room)
        
        # Update public rooms set if needed
        if room.settings.is_public:
            await RoomManager._add_to_public_rooms(room.id, len(room.players))
        else:
            await RoomManager._remove_from_public_rooms(room.id)
    
    @staticmethod
    async def delete_room(room_id: str):
        """Delete a room."""
        redis = redis_client.client
        
        room_key = f"{RoomManager.ROOM_PREFIX}{room_id}"
        players_key = f"{RoomManager.ROOM_PLAYERS_PREFIX}{room_id}"
        
        await redis.delete(room_key, players_key)
        await RoomManager._remove_from_public_rooms(room_id)
    
    @staticmethod
    async def add_player(room_id: str, player: Player):
        """Add a player to a room."""
        room = await RoomManager.get_room(room_id)
        if not room:
            return None
        
        room.players[player.id] = player
        await RoomManager.update_room(room)
        return room
    
    @staticmethod
    async def remove_player(room_id: str, player_id: str):
        """Remove a player from a room."""
        room = await RoomManager.get_room(room_id)
        if not room or player_id not in room.players:
            return None
        
        del room.players[player_id]
        
        # If room is empty or host left, delete room
        if not room.players or player_id == room.host_id:
            await RoomManager.delete_room(room_id)
            return None
        
        await RoomManager.update_room(room)
        return room
    
    @staticmethod
    async def update_player(room_id: str, player_id: str, **updates):
        """Update player fields."""
        room = await RoomManager.get_room(room_id)
        if not room or player_id not in room.players:
            return None
        
        player = room.players[player_id]
        for key, value in updates.items():
            if hasattr(player, key):
                setattr(player, key, value)
        
        await RoomManager.update_room(room)
        return room
    
    @staticmethod
    async def get_public_rooms() -> List[Dict]:
        """Get list of public rooms."""
        redis = redis_client.client
        
        # Get all public room IDs sorted by player count
        room_ids = await redis.zrevrange(RoomManager.PUBLIC_ROOMS_SET, 0, -1)
        
        rooms = []
        for room_id in room_ids:
            room = await RoomManager.get_room(room_id)
            if room and room.phase == RoomPhase.WAITING:
                rooms.append({
                    "id": room.id,
                    "player_count": len(room.players),
                    "max_players": room.settings.max_players,
                    "category_id": room.settings.category_id
                })
        
        return rooms
    
    @staticmethod
    async def _add_to_public_rooms(room_id: str, player_count: int):
        """Add room to public rooms sorted set."""
        redis = redis_client.client
        await redis.zadd(RoomManager.PUBLIC_ROOMS_SET, {room_id: player_count})
    
    @staticmethod
    async def _remove_from_public_rooms(room_id: str):
        """Remove room from public rooms set."""
        redis = redis_client.client
        await redis.zrem(RoomManager.PUBLIC_ROOMS_SET, room_id)
