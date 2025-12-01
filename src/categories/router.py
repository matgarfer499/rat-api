from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.categories.models import Category, CategoryTranslation
from src.categories.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryTranslationCreate,
    CategoryTranslationResponse,
    CategoryWithTranslations,
)
from src.database import get_db

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new category."""
    db_category = Category(key=category.key)
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category


@router.get("/", response_model=List[CategoryWithTranslations])
async def list_categories(
    language: str = "es",
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all categories with translations."""
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.translations))
        .offset(skip)
        .limit(limit)
    )
    categories = result.scalars().all()
    return categories


@router.get("/{category_id}", response_model=CategoryWithTranslations)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a category by ID with all its translations."""
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.translations))
        .where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found"
        )
    
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a category."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found"
        )
    
    await db.delete(category)
    await db.commit()


# ========== Category Translations Endpoints ==========


@router.post(
    "/{category_id}/translations",
    response_model=CategoryTranslationResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_category_translation(
    category_id: int,
    translation: CategoryTranslationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a translation for a category."""
    # Verify category exists
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found"
        )
    
    db_translation = CategoryTranslation(
        category_id=category_id,
        language=translation.language,
        name=translation.name
    )
    db.add(db_translation)
    await db.commit()
    await db.refresh(db_translation)
    return db_translation


@router.get(
    "/{category_id}/translations",
    response_model=List[CategoryTranslationResponse]
)
async def list_category_translations(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """List all translations for a category."""
    result = await db.execute(
        select(CategoryTranslation).where(CategoryTranslation.category_id == category_id)
    )
    translations = result.scalars().all()
    return translations
