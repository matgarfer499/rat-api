from enum import Enum

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from src.database import Base


class UserRole(str, Enum):
    """User role enum."""
    NORMAL = "normal"
    ADMIN = "admin"


class User(Base):
    """User model for database."""
    
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.NORMAL.value)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
