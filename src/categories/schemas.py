from pydantic import BaseModel, Field, ConfigDict


# ========== Category Schemas ==========

class CategoryBase(BaseModel):
    """Base schema for Category."""
    key: str = Field(..., min_length=1, max_length=100, description="Unique category key (e.g. 'animals')")


class CategoryCreate(CategoryBase):
    """Schema for creating a Category."""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a Category."""
    key: str | None = Field(None, min_length=1, max_length=100, description="Unique category key")


class CategoryResponse(CategoryBase):
    """Schema for Category response."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# ========== CategoryTranslation Schemas ==========

class CategoryTranslationBase(BaseModel):
    """Base schema for CategoryTranslation."""
    language: str = Field(..., min_length=2, max_length=5, description="Language code (e.g. 'es', 'en')")
    name: str = Field(..., min_length=1, max_length=200, description="Translated category name")


class CategoryTranslationCreate(CategoryTranslationBase):
    """Schema for creating a CategoryTranslation."""
    category_id: int = Field(..., gt=0, description="Category ID")


class CategoryTranslationUpdate(BaseModel):
    """Schema for updating a CategoryTranslation."""
    language: str | None = Field(None, min_length=2, max_length=5, description="Language code")
    name: str | None = Field(None, min_length=1, max_length=200, description="Translated category name")


class CategoryTranslationResponse(CategoryTranslationBase):
    """Schema for CategoryTranslation response."""
    id: int
    category_id: int
    
    model_config = ConfigDict(from_attributes=True)


# ========== Category with translations ==========

class CategoryWithTranslations(CategoryResponse):
    """Schema for Category with all its translations."""
    translations: list[CategoryTranslationResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class CategoryLocalized(BaseModel):
    """Schema for Category localized in a specific language."""
    id: int
    key: str
    name: str  # Translated name in the requested language
    
    model_config = ConfigDict(from_attributes=True)
