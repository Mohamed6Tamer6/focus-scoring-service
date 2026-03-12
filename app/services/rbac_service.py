# app/services/rbac_service.py

import time
from uuid import UUID
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.rbac_repository import (
    get_role_by_name, create_role as repo_create_role, get_all_roles as repo_get_all_roles,
    delete_role as repo_delete_role, get_permission_by_action_resource,
    create_permission as repo_create_permission, get_all_permissions as repo_get_all_permissions,
    get_role_permission, assign_permission_to_role as repo_assign_perm,
    revoke_permission_from_role as repo_revoke_perm, get_user_role,
    assign_role_to_user as repo_assign_role, revoke_role_from_user as repo_revoke_role,
    get_roles_for_user, resolve_user_permissions,
)
from app.models.rbac import Permission, Role, RolePermission, UserRole



@dataclass
class _CacheEntry:
    permissions: frozenset[str]
    expires_at: float

_perm_cache: dict[UUID, _CacheEntry] = {}
_DEFAULT_TTL = 300  # 5 دقايق


def _cache_get(user_id: UUID) -> Optional[frozenset[str]]:
    entry = _perm_cache.get(user_id)
    if entry and time.monotonic() < entry.expires_at:
        return entry.permissions
    _perm_cache.pop(user_id, None)
    return None


def _cache_set(user_id: UUID, perms: frozenset[str]) -> None:
    _perm_cache[user_id] = _CacheEntry(permissions=perms, expires_at=time.monotonic() + _DEFAULT_TTL)


def _cache_invalidate(user_id: UUID) -> None:
    _perm_cache.pop(user_id, None)


def _cache_clear() -> None:
    _perm_cache.clear()



def get_user_permissions(db: Session, user_id: UUID) -> frozenset[str]:
    cached = _cache_get(user_id)
    if cached is not None:
        return cached
    perms = resolve_user_permissions(db, user_id)
    _cache_set(user_id, perms)
    return perms



def create_role(db: Session, *, name: str, description: str | None = None) -> Role:
    if get_role_by_name(db, name):
        raise ValueError(f"Role '{name}' already exists.")
    return repo_create_role(db, name=name, description=description)


def get_all_roles(db: Session) -> list[Role]:
    return repo_get_all_roles(db)


def delete_role(db: Session, role_id: UUID) -> None:
    repo_delete_role(db, role_id)
    _cache_clear()



def create_permission(db: Session, *, action: str, resource: str, description: str | None = None) -> Permission:
    if get_permission_by_action_resource(db, action, resource):
        raise ValueError(f"Permission '{action}:{resource}' already exists.")
    return repo_create_permission(db, action=action, resource=resource, description=description)


def get_all_permissions(db: Session) -> list[Permission]:
    return repo_get_all_permissions(db)



def assign_permission_to_role(db: Session, *, role_id: UUID, permission_id: UUID) -> RolePermission:
    if get_role_permission(db, role_id, permission_id):
        raise ValueError("Permission already assigned to this role.")
    rp = repo_assign_perm(db, role_id=role_id, permission_id=permission_id)
    _cache_clear()
    return rp


def revoke_permission_from_role(db: Session, *, role_id: UUID, permission_id: UUID) -> None:
    repo_revoke_perm(db, role_id=role_id, permission_id=permission_id)
    _cache_clear()



def assign_role_to_user(db: Session, *, user_id: UUID, role_id: UUID, assigned_by: UUID | None = None) -> UserRole:
    if get_user_role(db, user_id, role_id):
        raise ValueError("User already has this role.")
    ur = repo_assign_role(db, user_id=user_id, role_id=role_id, assigned_by=assigned_by)
    _cache_invalidate(user_id)
    return ur


def revoke_role_from_user(db: Session, *, user_id: UUID, role_id: UUID) -> None:
    repo_revoke_role(db, user_id=user_id, role_id=role_id)
    _cache_invalidate(user_id)


def get_user_roles(db: Session, user_id: UUID) -> list[Role]:
    return get_roles_for_user(db, user_id)