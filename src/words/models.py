from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.database import Base


class Word(Base):
    """Word model for database."""
    
    __tablename__ = "word"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    
    # Relationship with Category (many-to-one)
    category = relationship("Category", back_populates="words")
    
    # Relationship with WordTranslation (one-to-many)
    translations = relationship("WordTranslation", back_populates="word", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Word(id={self.id}, key='{self.key}', category_id={self.category_id})>"


class WordTranslation(Base):
    """WordTranslation model for word translations."""
    
    __tablename__ = "word_translation"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    word_id = Column(Integer, ForeignKey("word.id"), nullable=False)
    language = Column(String(5), nullable=False, index=True)  # "es", "en", etc.
    value = Column(String(200), nullable=False)
    
    # Relationship with Word (many-to-one)
    word = relationship("Word", back_populates="translations")
    
    def __repr__(self):
        return f"<WordTranslation(id={self.id}, word_id={self.word_id}, language='{self.language}', value='{self.value}')>"
