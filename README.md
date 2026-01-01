# RAT API

Backend API for the RAT multiplayer word game. Built with FastAPI, Socket.IO, and Redis.

## Overview

RAT is a social deduction game where players receive a secret word from a category. One player (the impostor) doesn't know the word and must blend in during discussions. Players vote to identify the impostor.

### Game Roles

- **Civilian**: Knows the secret word
- **Impostor**: Doesn't know the word, must pretend to know it
- **Detective** (optional): Special civilian role
- **Joker** (optional): Wildcard role

### Game Phases

1. **Waiting**: Players join the room and ready up
2. **Role Reveal**: Players see their role and word (10 seconds)
3. **Playing**: Discussion phase (5 minutes)
4. **Voting**: Players vote for the impostor (30 seconds)
5. **Results**: Winner is revealed

## Tech Stack

- **FastAPI** - Web framework
- **Socket.IO** - Real-time WebSocket communication
- **Redis** - Pub/Sub for multi-instance communication and room state
- **Pydantic** - Data validation

## Requirements

- Python 3.11+
- Redis server
- Docker (optional)

## Getting Started

### Using Docker (Recommended)

```bash
docker-compose up
```

This starts:
- API server on port 8000
- Redis server on port 6379

### Manual Setup

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start Redis:

```bash
redis-server
```

4. Run the API:

```bash
uvicorn src.main:app --reload
```

## API Endpoints

### Health

- `GET /` - Hello World
- `GET /health` - Health check

### Authentication

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get JWT token

### Categories

- `GET /categories` - List all categories
- `POST /categories` - Create a category

### Words

- `GET /words` - List words
- `POST /words` - Create a word

### Game

- `GET /game/random-word` - Get a random word from categories
- `POST /game/start` - Start a game in a room

### Rooms

- `GET /rooms` - List public rooms
- `POST /rooms` - Create a room
- `GET /rooms/{room_id}` - Get room details

## WebSocket Events

Connect to `/socket.io` for real-time game communication.

### Client Events (emit)

- `join_room` - Join a game room
- `leave_room` - Leave a room
- `ready` - Toggle ready status
- `start_game` - Start the game (host only)
- `vote` - Cast a vote
- `request_voting` - Request to start voting phase

### Server Events (listen)

- `room_state` - Full room state update
- `player_joined` - Player joined the room
- `player_left` - Player left the room
- `player_ready` - Player ready status changed
- `game_started` - Game has started
- `phase_change` - Game phase changed
- `vote_update` - Vote was cast
- `game_result` - Game ended with result
- `error` - Error message

## Project Structure

```
src/
  main.py              # FastAPI app entry point
  database.py          # Database configuration
  seed.py              # Database seeding
  logging_config.py    # Logging setup
  auth/                # Authentication module
  categories/          # Categories CRUD
  words/               # Words CRUD
  game/                # Game logic
  rooms/               # Room management
  redis/               # Redis client
  sockets/             # Socket.IO events
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./test.db` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |

## Development

The API auto-seeds the database with initial categories and words on first startup if the database is empty.

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc