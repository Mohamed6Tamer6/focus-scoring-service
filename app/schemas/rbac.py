# app/schemas/rbac.py

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, field_validator


class PermissionCreate(BaseModel):
    action: str
    resource: str
    description: str | None = None

    @field_validator("action", "resource")
    @classmethod
    def normalize(cls, v: str) -> str:
        if ":" in v:
            raise ValueError("Don't include : — use separate action and resource fields.")
        return v.strip().lower()


class PermissionRead(BaseModel):
    id: UUID
    action: str
    resource: str
    codename: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_")


class RoleRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    permissions: list[PermissionRead] = []

    model_config = {"from_attributes": True}


class AssignPermissionToRole(BaseModel):
    permission_id: UUID


class AssignRoleToUser(BaseModel):
    user_id: UUID
    role_id: UUID


class RevokeRoleFromUser(BaseModel):
    user_id: UUID
    role_id: UUID


class UserPermissionsRead(BaseModel):
    user_id: UUID
    roles: list[str]
    permissions: list[str]