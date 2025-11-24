from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from src.categories.schemas import CategoryResponse


# ========== Word Schemas ==========

class WordBase(BaseModel):
    """Base schema for Word."""
    key: str = Field(..., min_length=1, max_length=100, description="Unique word key (e.g. 'dog')")
    category_id: int = Field(..., gt=0, description="Category ID this word belongs to")


class WordCreate(WordBase):
    """Schema for creating a Word."""
    pass


class WordUpdate(BaseModel):
    """Schema for updating a Word."""
    key: str | None = Field(None, min_length=1, max_length=100, description="Unique word key")
    category_id: int | None = Field(None, gt=0, description="Category ID this word belongs to")


class WordResponse(WordBase):
    """Schema for Word response."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# ========== WordTranslation Schemas ==========

class WordTranslationBase(BaseModel):
    """Base schema for WordTranslation."""
    language: str = Field(..., min_length=2, max_length=5, description="Language code (e.g. 'es', 'en')")
    value: str = Field(..., min_length=1, max_length=200, description="Translated word value")


class WordTranslationCreate(WordTranslationBase):
    """Schema for creating a WordTranslation."""
    word_id: int = Field(..., gt=0, description="Word ID")


class WordTranslationUpdate(BaseModel):
    """Schema for updating a WordTranslation."""
    language: str | None = Field(None, min_length=2, max_length=5, description="Language code")
    value: str | None = Field(None, min_length=1, max_length=200, description="Translated word value")


class WordTranslationResponse(WordTranslationBase):
    """Schema for WordTranslation response."""
    id: int
    word_id: int
    
    model_config = ConfigDict(from_attributes=True)


# ========== Word with translations ==========

class WordWithTranslations(WordResponse):
    """Schema for Word with all its translations."""
    translations: list[WordTranslationResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class WordLocalized(BaseModel):
    """Schema for Word localized in a specific language."""
    id: int
    key: str
    value: str  # Translated value in the requested language
    category_id: int
    
    model_config = ConfigDict(from_attributes=True)


class WordWithCategory(WordResponse):
    """Schema for Word with its related category."""
    category: "CategoryResponse"
    
    model_config = ConfigDict(from_attributes=True)
