"""Room and player models for multiplayer game."""
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator


class RoomPhase(str, Enum):
    """Game phases."""
    WAITING = "waiting"
    HINTS = "hints"
    VOTING = "voting"
    RESULTS = "results"


class PlayerRole(str, Enum):
    """Player roles in the game."""
    CIVILIAN = "civilian"
    IMPOSTOR = "impostor"


class Player(BaseModel):
    """Player in a room."""
    id: str
    username: str
    user_id: Optional[int] = None  # None for guest players
    is_ready: bool = False
    role: Optional[PlayerRole] = None
    hint: Optional[str] = None
    vote: Optional[str] = None  # player_id they voted for
    is_host: bool = False
    
    def dict(self, *args, **kwargs):
        """Convert to dict with enum values."""
        d = super().dict(*args, **kwargs)
        if self.role:
            d['role'] = self.role.value
        return d


class RoomSettings(BaseModel):
    """Room configuration."""
    max_players: int = Field(default=8, ge=3, le=12)
    category_id: int
    is_public: bool = True
    password: Optional[str] = None


class Room(BaseModel):
    """Game room state."""
    id: str
    host_id: str  # player_id of the host
    settings: RoomSettings
    phase: RoomPhase = RoomPhase.WAITING
    players: Dict[str, Player] = {}  # player_id -> Player
    word: Optional[str] = None
    round_number: int = 0
    created_at: float
    
    def dict(self, *args, **kwargs):
        """Convert to dict with enum values."""
        d = super().dict(*args, **kwargs)
        d['phase'] = self.phase.value
        d['players'] = {k: v.dict() for k, v in self.players.items()}
        return d


# Request/Response models
class CreateRoomRequest(BaseModel):
    """Request to create a new room."""
    username: str
    category_id: int
    max_players: int = Field(default=8, ge=3, le=12)
    is_public: bool = True
    password: Optional[str] = None
    
    @validator('password', always=True)
    def validate_password(cls, v, values):
        is_public = values.get('is_public', True)
        if not is_public and not v:
            raise ValueError('Private rooms must have a password')
        if is_public and v:
            raise ValueError('Public rooms cannot have a password')
        return v


class JoinRoomRequest(BaseModel):
    """Request to join a room."""
    username: str
    room_id: str
    password: Optional[str] = None


class RoomResponse(BaseModel):
    """Room information response."""
    id: str
    host_id: str
    phase: str
    player_count: int
    max_players: int
    is_public: bool
    has_password: bool


class PublicRoom(BaseModel):
    """Public room listing."""
    id: str
    player_count: int
    max_players: int
    category_id: int


# Socket.IO event data models
class GameEventData(BaseModel):
    """Generic game event data."""
    event_type: str
    data: dict
