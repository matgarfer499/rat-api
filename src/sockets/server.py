"""Socket.IO server configuration."""
import socketio
from src.logging_config import get_logger


logger = get_logger(__name__)

# Create Socket.IO async server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Update in production
    logger=False,
    engineio_logger=False
)

# Create ASGI application
socket_app = socketio.ASGIApp(
    sio,
    socketio_path='socket.io'
)

# Import event modules to register handlers - THIS IS CRITICAL!
from src.sockets import connection_events  # noqa: F401, E402
from src.sockets import room_events  # noqa: F401, E402
from src.sockets import player_events  # noqa: F401, E402
from src.sockets import game_events  # noqa: F401, E402
logger.info("✅ Socket.IO event handlers registered!")
