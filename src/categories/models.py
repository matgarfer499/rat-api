from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.database import Base


class Category(Base):
    """Category model for database."""
    
    __tablename__ = "category"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    
    # Relationship with Words (one-to-many)
    words = relationship("Word", back_populates="category", cascade="all, delete-orphan")
    
    # Relationship with CategoryTranslation (one-to-many)
    translations = relationship("CategoryTranslation", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Category(id={self.id}, key='{self.key}')>"


class CategoryTranslation(Base):
    """CategoryTranslation model for category translations."""
    
    __tablename__ = "category_translation"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    language = Column(String(5), nullable=False, index=True)  # "es", "en", etc.
    name = Column(String(200), nullable=False)
    
    # Relationship with Category (many-to-one)
    category = relationship("Category", back_populates="translations")
    
    def __repr__(self):
        return f"<CategoryTranslation(id={self.id}, category_id={self.category_id}, language='{self.language}', name='{self.name}')>"
