from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.words.models import Word, WordTranslation

router = APIRouter(prefix="/game", tags=["Game"])


@router.get("/random-word")
async def get_random_word(
    category_ids: List[int] = Query(..., description="List of category IDs"),
    language: str = Query(..., min_length=2, max_length=5, description="Language code (e.g. 'es', 'en')"),
):
    """
    Get a random word from the specified categories in the requested language.
    
    This is optimized to avoid fetching all words - it uses SQL RANDOM() to select one word.
    """
    async with async_session_maker() as db:
        # Get a random word from the selected categories
        query = (
            select(Word)
            .where(Word.category_id.in_(category_ids))
            .order_by(func.random())
            .limit(1)
        )
        
        result = await db.execute(query)
        word = result.scalar_one_or_none()
        
        if not word:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No words found in the selected categories"
            )
        
        # Get translation for the word
        translation_query = select(WordTranslation).where(
            WordTranslation.word_id == word.id,
            WordTranslation.language == language
        )
        
        translation_result = await db.execute(translation_query)
        translation = translation_result.scalar_one_or_none()
        
        if not translation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No translation found for language '{language}'"
            )
        
        return {
            "word_id": word.id,
            "word_key": word.key,
            "word_value": translation.value,
            "category_id": word.category_id,
            "language": language
        }
