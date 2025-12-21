from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from src.game.logic import get_random_word as get_random_word_logic

router = APIRouter(prefix="/game", tags=["Game"])


@router.get("/random-word")
async def get_random_word(
    category_ids: List[int] = Query(..., description="List of category IDs"),
    language: str = Query(..., min_length=2, max_length=5, description="Language code (e.g. 'es', 'en')"),
    exclude_word: str = Query(None, description="Word to exclude (avoid repetition)"),
):
    """
    Get a random word from the specified categories in the requested language.
    
    This is optimized to avoid fetching all words - it uses SQL RANDOM() to select one word.
    Optionally excludes a specific word to avoid repetition between games.
    """
    result = await get_random_word_logic(category_ids, language, exclude_word)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No words found in the selected categories or no translation found"
        )
    
    return result
