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
    exclude_word: str = Query(None, description="Word to exclude (avoid repetition)"),
):
    """
    Get a random word from the specified categories in the requested language.
    
    This is optimized to avoid fetching all words - it uses SQL RANDOM() to select one word.
    Optionally excludes a specific word to avoid repetition between games.
    """
    async with async_session_maker() as db:
        # Get a random word from the selected categories
        query = (
            select(Word)
            .where(Word.category_id.in_(category_ids))
            .order_by(func.random())
            .limit(5)  # Get a few options to filter from
        )
        
        result = await db.execute(query)
        words = result.scalars().all()
        
        if not words:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No words found in the selected categories"
            )
        
        # Find a word that's not excluded
        selected_word = None
        for word in words:
            # Get translation for this word
            translation_query = select(WordTranslation).where(
                WordTranslation.word_id == word.id,
                WordTranslation.language == language
            )
            translation_result = await db.execute(translation_query)
            translation = translation_result.scalar_one_or_none()
            
            if translation:
                # Check if this word should be excluded
                if exclude_word and translation.value.lower() == exclude_word.lower():
                    continue  # Skip this word, try next
                selected_word = word
                selected_translation = translation
                break
        
        # If all words were excluded (unlikely), just use the first one
        if not selected_word:
            selected_word = words[0]
            translation_query = select(WordTranslation).where(
                WordTranslation.word_id == selected_word.id,
                WordTranslation.language == language
            )
            translation_result = await db.execute(translation_query)
            selected_translation = translation_result.scalar_one_or_none()
            
            if not selected_translation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No translation found for language '{language}'"
                )
        
        return {
            "word_id": selected_word.id,
            "word_key": selected_word.key,
            "word_value": selected_translation.value,
            "category_id": selected_word.category_id,
            "language": language
        }
