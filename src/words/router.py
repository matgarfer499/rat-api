from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.words.models import Word, WordTranslation
from src.words.schemas import (
    WordCreate,
    WordResponse,
    WordTranslationCreate,
    WordTranslationResponse,
    WordWithTranslations,
)

router = APIRouter(prefix="/words", tags=["Words"])


@router.post("/", response_model=WordResponse, status_code=status.HTTP_201_CREATED)
async def create_word(
    word: WordCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new word."""
    db_word = Word(key=word.key, category_id=word.category_id)
    db.add(db_word)
    await db.commit()
    await db.refresh(db_word)
    return db_word


@router.get("/", response_model=List[WordResponse])
async def list_words(
    skip: int = 0,
    limit: int = 100,
    category_id: int | None = None,
    db: AsyncSession = Depends(get_db)
):
    """List all words, optionally filtered by category."""
    query = select(Word)
    
    if category_id:
        query = query.where(Word.category_id == category_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    words = result.scalars().all()
    return words


@router.get("/{word_id}", response_model=WordWithTranslations)
async def get_word(
    word_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a word by ID with all its translations."""
    result = await db.execute(
        select(Word).where(Word.id == word_id)
    )
    word = result.scalar_one_or_none()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word with id {word_id} not found"
        )
    
    return word


@router.delete("/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_word(
    word_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a word."""
    result = await db.execute(
        select(Word).where(Word.id == word_id)
    )
    word = result.scalar_one_or_none()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word with id {word_id} not found"
        )
    
    await db.delete(word)
    await db.commit()


# ========== Word Translations Endpoints ==========


@router.post(
    "/{word_id}/translations",
    response_model=WordTranslationResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_word_translation(
    word_id: int,
    translation: WordTranslationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a translation for a word."""
    # Verify word exists
    result = await db.execute(
        select(Word).where(Word.id == word_id)
    )
    word = result.scalar_one_or_none()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word with id {word_id} not found"
        )
    
    db_translation = WordTranslation(
        word_id=word_id,
        language=translation.language,
        value=translation.value
    )
    db.add(db_translation)
    await db.commit()
    await db.refresh(db_translation)
    return db_translation


@router.get(
    "/{word_id}/translations",
    response_model=List[WordTranslationResponse]
)
async def list_word_translations(
    word_id: int,
    db: AsyncSession = Depends(get_db)
):
    """List all translations for a word."""
    result = await db.execute(
        select(WordTranslation).where(WordTranslation.word_id == word_id)
    )
    translations = result.scalars().all()
    return translations
