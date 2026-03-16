from pydantic import BaseModel, EmailStr
from uuid import UUID


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"
    admin_id: UUID | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    roles: list[str] = []
    admin_id: UUID | None = None
    admin_info: dict | None = None

    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    admin_id: UUID | None = None