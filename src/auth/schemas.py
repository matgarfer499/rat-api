from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    """Base schema for User."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")


class UserCreate(UserBase):
    """Schema for creating a User."""
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class UserResponse(UserBase):
    """Schema for User response."""
    id: int
    role: str
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Schema for JWT token data."""
    username: str | None = None
    role: str | None = None
