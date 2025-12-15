"""Game logic for multiplayer mode."""
import random
import time
from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.words.models import Word, WordTranslation
from src.rooms.models import Room, Player, RoomPhase, PlayerRole, GameState, GameResult
from src.rooms.redis_manager import RoomManager
from src.logging_config import get_logger

logger = get_logger(__name__)

# Game timing constants (in seconds)
ROLE_REVEAL_DURATION = 10  # 10 seconds to see role/word
PLAYING_DURATION = 300     # 5 minutes for discussion
VOTING_DURATION = 30       # 30 seconds to vote


async def get_random_word(category_id: int, language: str = "es", exclude_word: Optional[str] = None) -> Optional[str]:
    """Get a random word from the specified category, optionally excluding a word."""
    async with async_session_maker() as db:
        # Get a few random words from the category to filter from
        query = (
            select(Word)
            .where(Word.category_id == category_id)
            .order_by(func.random())
            .limit(5)
        )
        
        result = await db.execute(query)
        words = result.scalars().all()
        
        if not words:
            logger.warning(f"No words found in category {category_id}")
            return None
        
        # Find a word that's not excluded
        for word in words:
            translation_query = select(WordTranslation).where(
                WordTranslation.word_id == word.id,
                WordTranslation.language == language
            )
            
            translation_result = await db.execute(translation_query)
            translation = translation_result.scalar_one_or_none()
            
            if translation:
                # Check if should be excluded
                if exclude_word and translation.value.lower() == exclude_word.lower():
                    continue  # Skip, try next word
                return translation.value
        
        # If all words were excluded, fallback to first one
        word = words[0]
        translation_query = select(WordTranslation).where(
            WordTranslation.word_id == word.id,
            WordTranslation.language == language
        )
        translation_result = await db.execute(translation_query)
        translation = translation_result.scalar_one_or_none()
        
        if not translation:
            logger.warning(f"No translation found for word {word.id} in language {language}")
            return None
        
        return translation.value


def assign_roles(players: List[Player], exclude_player_id: Optional[str] = None) -> Tuple[List[Player], str]:
    """
    Assign roles to players. One impostor, rest are civilians.
    Optionally excludes a player from being selected as impostor (to avoid repetition).
    Returns updated players list and the impostor_id.
    """
    if len(players) < 3:
        raise ValueError("Need at least 3 players to start game")
    
    # Filter out excluded player if possible
    available_indices = list(range(len(players)))
    if exclude_player_id and len(players) > 1:
        for i, player in enumerate(players):
            if player.id == exclude_player_id:
                available_indices.remove(i)
                break
    
    # If no available indices (shouldn't happen), use all
    if not available_indices:
        available_indices = list(range(len(players)))
    
    # Randomly select impostor from available
    impostor_index = random.choice(available_indices)
    impostor_id = players[impostor_index].id
    
    for i, player in enumerate(players):
        if i == impostor_index:
            player.role = PlayerRole.IMPOSTOR
        else:
            player.role = PlayerRole.CIVILIAN
        # Reset game-specific fields
        player.vote = None
        player.wants_to_vote = False
        player.is_ready = False
    
    return players, impostor_id


async def start_game(room: Room, language: str = "es") -> Optional[Room]:
    """
    Start a new game in the room.
    - Assign roles (1 impostor, rest civilians)
    - Get random word (avoiding last word)
    - Set phase to ROLE_REVEAL
    Uses room.last_word and room.last_starting_player_id to avoid repetition.
    """
    logger.info(f"🎮 Starting game in room {room.id}")
    
    players_list = list(room.players.values())
    
    if len(players_list) < 3:
        logger.warning(f"Not enough players in room {room.id}: {len(players_list)}")
        return None
    
    # Get random word for the category, excluding last word
    word = await get_random_word(
        room.settings.category_id, 
        language, 
        exclude_word=room.last_word
    )
    if not word:
        logger.error(f"Could not get word for room {room.id}")
        return None
    
    # Assign roles, excluding last impostor/starting player
    updated_players, impostor_id = assign_roles(
        players_list, 
        exclude_player_id=room.last_starting_player_id
    )
    
    # Assign word to civilians
    for player in updated_players:
        if player.role == PlayerRole.CIVILIAN:
            player.word = word
        else:
            player.word = None  # Impostor doesn't see the word
    
    # Update room with cache
    room.players = {p.id: p for p in updated_players}
    room.phase = RoomPhase.ROLE_REVEAL
    room.round_number += 1
    room.last_word = word  # Cache for next game
    room.last_starting_player_id = impostor_id  # Cache for next game
    room.game_state = GameState(
        word=word,
        impostor_id=impostor_id,
        phase_start_time=time.time(),
        votes_submitted=0
    )
    
    await RoomManager.update_room(room)
    
    logger.info(f"🎮 Game started in room {room.id}: word='{word}', impostor={impostor_id} (excluded last: word='{room.last_word}', player='{room.last_starting_player_id}')")
    
    return room


async def transition_to_playing(room: Room) -> Room:
    """Transition from ROLE_REVEAL to PLAYING phase."""
    room.phase = RoomPhase.PLAYING
    room.game_state.phase_start_time = time.time()
    await RoomManager.update_room(room)
    logger.info(f"🎮 Room {room.id} transitioned to PLAYING phase")
    return room


async def request_voting(room: Room, player_id: str) -> Tuple[Room, bool]:
    """
    Player requests to start voting phase.
    Returns (updated_room, should_start_voting).
    Voting starts if more than half the players want to vote.
    """
    if room.phase != RoomPhase.PLAYING:
        return room, False
    
    if player_id not in room.players:
        return room, False
    
    # Mark player as wanting to vote
    room.players[player_id].wants_to_vote = True
    
    # Check if majority wants to vote
    total_players = len(room.players)
    wants_to_vote_count = sum(1 for p in room.players.values() if p.wants_to_vote)
    majority_threshold = (total_players // 2) + 1
    
    should_start_voting = wants_to_vote_count >= majority_threshold
    
    if should_start_voting:
        room.phase = RoomPhase.VOTING
        room.game_state.phase_start_time = time.time()
        logger.info(f"🗳️ Room {room.id} transitioned to VOTING phase (majority requested)")
    
    await RoomManager.update_room(room)
    
    return room, should_start_voting


async def submit_vote(room: Room, voter_id: str, voted_for_id: str) -> Tuple[Room, bool]:
    """
    Submit a vote.
    Returns (updated_room, all_voted).
    """
    if room.phase != RoomPhase.VOTING:
        return room, False
    
    if voter_id not in room.players or voted_for_id not in room.players:
        return room, False
    
    if voter_id == voted_for_id:
        return room, False  # Can't vote for yourself
    
    # Record vote
    room.players[voter_id].vote = voted_for_id
    room.game_state.votes_submitted = sum(1 for p in room.players.values() if p.vote is not None)
    
    await RoomManager.update_room(room)
    
    # Check if everyone has voted
    all_voted = room.game_state.votes_submitted >= len(room.players)
    
    logger.info(f"🗳️ {room.players[voter_id].username} voted for {room.players[voted_for_id].username} in room {room.id}")
    
    return room, all_voted


async def calculate_results(room: Room) -> Room:
    """
    Calculate game results based on votes.
    - Count votes for each player
    - Determine most voted
    - If most voted is impostor -> civilians win
    - If most voted is civilian -> impostor wins
    """
    if room.phase != RoomPhase.VOTING:
        return room
    
    # Count votes
    vote_counts = {}
    for player in room.players.values():
        if player.vote:
            vote_counts[player.vote] = vote_counts.get(player.vote, 0) + 1
    
    # Find most voted (tie goes to first alphabetically by username)
    if not vote_counts:
        # No votes - impostor wins by default
        room.game_state.result = GameResult.IMPOSTOR_WINS
        room.game_state.most_voted_id = None
    else:
        # Find max vote count
        max_votes = max(vote_counts.values())
        most_voted = [pid for pid, count in vote_counts.items() if count == max_votes]
        
        # If tie, sort by username
        if len(most_voted) > 1:
            most_voted.sort(key=lambda pid: room.players[pid].username.lower())
        
        most_voted_id = most_voted[0]
        room.game_state.most_voted_id = most_voted_id
        
        # Determine winner
        if most_voted_id == room.game_state.impostor_id:
            room.game_state.result = GameResult.CIVILIANS_WIN
            logger.info(f"🎉 Civilians WIN in room {room.id} - impostor was caught!")
        else:
            room.game_state.result = GameResult.IMPOSTOR_WINS
            logger.info(f"🎭 Impostor WINS in room {room.id} - wrong player voted!")
    
    # Transition to results phase
    room.phase = RoomPhase.RESULTS
    room.game_state.phase_start_time = time.time()
    
    await RoomManager.update_room(room)
    
    return room


async def return_to_lobby(room: Room) -> Room:
    """
    Return room to waiting/lobby phase after game ends.
    Reset all game state.
    """
    # Reset all players
    for player in room.players.values():
        player.role = None
        player.word = None
        player.vote = None
        player.is_ready = False
        player.wants_to_vote = False
    
    # Reset room
    room.phase = RoomPhase.WAITING
    room.game_state = None
    
    await RoomManager.update_room(room)
    
    logger.info(f"🏠 Room {room.id} returned to lobby")
    
    return room
