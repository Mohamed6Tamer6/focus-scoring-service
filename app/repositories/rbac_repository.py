# app/repositories/rbac_repository.py

from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session

from app.models.rbac import Permission, Role, RolePermission, UserRole



def get_role_by_id(db: Session, role_id: UUID) -> Optional[Role]:
    return db.query(Role).filter(Role.id == role_id).first()


def get_role_by_name(db: Session, name: str) -> Optional[Role]:
    return db.query(Role).filter(Role.name == name).first()


def get_all_roles(db: Session) -> list[Role]:
    return db.query(Role).order_by(Role.name).all()


def create_role(db: Session, *, name: str, description: str | None) -> Role:
    role = Role(name=name, description=description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: UUID) -> None:
    db.query(Role).filter(Role.id == role_id).delete()
    db.commit()



def get_permission_by_id(db: Session, perm_id: UUID) -> Optional[Permission]:
    return db.query(Permission).filter(Permission.id == perm_id).first()


def get_permission_by_action_resource(db: Session, action: str, resource: str) -> Optional[Permission]:
    return db.query(Permission).filter(
        Permission.action == action,
        Permission.resource == resource,
    ).first()


def get_all_permissions(db: Session) -> list[Permission]:
    return db.query(Permission).order_by(Permission.resource, Permission.action).all()


def create_permission(db: Session, *, action: str, resource: str, description: str | None) -> Permission:
    perm = Permission(action=action, resource=resource, description=description)
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm



def get_role_permission(db: Session, role_id: UUID, permission_id: UUID) -> Optional[RolePermission]:
    return db.query(RolePermission).filter(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission_id,
    ).first()


def assign_permission_to_role(db: Session, *, role_id: UUID, permission_id: UUID) -> RolePermission:
    rp = RolePermission(role_id=role_id, permission_id=permission_id)
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return rp


def revoke_permission_from_role(db: Session, *, role_id: UUID, permission_id: UUID) -> None:
    db.query(RolePermission).filter(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission_id,
    ).delete()
    db.commit()



def get_user_role(db: Session, user_id: UUID, role_id: UUID) -> Optional[UserRole]:
    return db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id,
    ).first()


def get_roles_for_user(db: Session, user_id: UUID) -> list[Role]:
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    return [ur.role for ur in user_roles]


def assign_role_to_user(db: Session, *, user_id: UUID, role_id: UUID, assigned_by: UUID | None = None) -> UserRole:
    ur = UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
    db.add(ur)
    db.commit()
    db.refresh(ur)
    return ur


def revoke_role_from_user(db: Session, *, user_id: UUID, role_id: UUID) -> None:
    db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id,
    ).delete()
    db.commit()


def resolve_user_permissions(db: Session, user_id: UUID) -> frozenset[str]:
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    
    # Check if user has 'admin' role
    is_admin = any(ur.role.name == "admin" and ur.role.is_active for ur in user_roles)
    
    if is_admin:
        # If admin, they get all permissions in the system
        all_perms = db.query(Permission).all()
        return frozenset(p.codename for p in all_perms) | frozenset(["manage:rbac", "admin"]) # Ensure core perms are there even if not in DB yet

    perms: set[str] = set()
    for ur in user_roles:
        if ur.role.is_active:
            for rp in ur.role.role_permissions:
                perms.add(rp.permission.codename)
    return frozenset(perms)