# app/api/routes/rbac.py

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.rbac import (
    AssignPermissionToRole, AssignRoleToUser,
    PermissionCreate, PermissionRead,
    RoleCreate, RoleRead,
    RevokeRoleFromUser, UserPermissionsRead,
)
from app.services import rbac_service

router = APIRouter(prefix="/admin/rbac", tags=["RBAC"])


def require_permission(permission: str):

    def _dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        perms = rbac_service.get_user_permissions(db, current_user.id)
        if permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "permission_denied",
                    "required": permission,
                },
            )
        return current_user
    return Depends(_dependency)



@router.post("/permissions", response_model=PermissionRead, status_code=201)
def create_permission(
    body: PermissionCreate,
    db: Session = Depends(get_db),
    _: User = require_permission("manage:rbac"),
):
    try:
        return rbac_service.create_permission(db, action=body.action, resource=body.resource, description=body.description)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(
    db: Session = Depends(get_db),
    _: User = require_permission("manage:rbac"),
):
    return rbac_service.get_all_permissions(db)



@router.post("/roles", response_model=RoleRead, status_code=201)
def create_role(
    body: RoleCreate,
    db: Session = Depends(get_db),
    _: User = require_permission("manage:rbac"),
):
    try:
        return rbac_service.create_role(db, name=body.name, description=body.description)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    db: Session = Depends(get_db),
    _: User = require_permission("manage:rbac"),
):
    return rbac_service.get_all_roles(db)


@router.post("/roles/{role_id}/permissions", status_code=204)
def assign_permission_to_role(
    role_id: UUID,
    body: AssignPermissionToRole,
    db: Session = Depends(get_db),
    _: User = require_permission("manage:rbac"),
):
    try:
        rbac_service.assign_permission_to_role(db, role_id=role_id, permission_id=body.permission_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=204)
def revoke_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    db: Session = Depends(get_db),
    _: User = require_permission("manage:rbac"),
):
    rbac_service.revoke_permission_from_role(db, role_id=role_id, permission_id=permission_id)



@router.post("/users/roles", status_code=204)
def assign_role_to_user(
    body: AssignRoleToUser,
    db: Session = Depends(get_db),
    admin: User = require_permission("manage:rbac"),
):
    try:
        rbac_service.assign_role_to_user(db, user_id=body.user_id, role_id=body.role_id, assigned_by=admin.id)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/users/roles", status_code=204)
def revoke_role_from_user(
    body: RevokeRoleFromUser,
    db: Session = Depends(get_db),
    _: User = require_permission("manage:rbac"),
):
    rbac_service.revoke_role_from_user(db, user_id=body.user_id, role_id=body.role_id)


@router.get("/users/{user_id}/permissions", response_model=UserPermissionsRead)
def get_user_permissions(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = require_permission("manage:rbac"),
):
    roles = rbac_service.get_user_roles(db, user_id)
    perms = rbac_service.get_user_permissions(db, user_id)
    return UserPermissionsRead(
        user_id=user_id,
        roles=[r.name for r in roles],
        permissions=sorted(perms),
    )