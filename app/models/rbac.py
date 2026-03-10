
# app//models/rbac.py

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Index, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    role_permissions = relationship("RolePermission",back_populates="role",cascade="all, delete-orphan")
    user_roles = relationship("UserRole",back_populates="role",cascade="all, delete-orphan")

    @property
    def permissions(self):
        return [rp.permission for rp in self.role_permissions]

    def __repr__(self):
        return f"<Role name={self.name!r}>"


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String(64),nullable=False)
    resource = Column(String(64),nullable=False)
    description = Column(String(255),nullable=True)
    created_at  = Column(DateTime(timezone=True),nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("action", "resource", name="uq_permission_action_resource"),
        Index("ix_permission_action_resource", "action", "resource"),
    )

    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

    @property
    def codename(self) -> str:
        return f"{self.action}:{self.resource}"

    def __repr__(self):
        return f"<Permission {self.codename!r}>"


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    role = relationship("Role", back_populates="user_roles")
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])

    def __repr__(self):
        return f"<UserRole user={self.user_id} role={self.role_id}>"


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id",       ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role = relationship("Role",back_populates="role_permissions")
    permission = relationship("Permission",back_populates="role_permissions")

    def __repr__(self):
        return f"<RolePermission role={self.role_id} perm={self.permission_id}>"