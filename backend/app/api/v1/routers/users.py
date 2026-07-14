"""User management endpoints (admin)."""
from __future__ import annotations

from typing import Optional

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import DbSession, frontend_base_url, require_admin
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.assignment import MyCourseOut
from app.schemas.common import Message, Page
from app.schemas.user import UserCreate, UserCreateResponse, UserOut, UserUpdate
from app.services.assignment_service import AssignmentService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=Page[UserOut])
def list_users(
    db: DbSession,
    q: Optional[str] = Query(None, description="Search name / username / email"),
    role: Optional[RoleName] = None,
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    users, total = UserService(db).list_users(
        query=q, role=role, department_id=department_id, is_active=is_active,
        offset=(page - 1) * page_size, limit=page_size,
    )
    return Page[UserOut](
        items=[UserOut.from_model(u) for u in users],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, request: Request, db: DbSession):
    user, setup_token = UserService(db).create_user(payload, base_url=frontend_base_url(request))
    out = UserCreateResponse.from_model(user)
    out.setup_token = setup_token
    return out


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: DbSession):
    return UserOut.from_model(UserService(db).get_user(user_id))


@router.get("/{user_id}/courses", response_model=list[MyCourseOut])
def user_courses(user_id: int, db: DbSession):
    """An employee's assigned courses & progress, for admin review."""
    user = UserService(db).get_user(user_id)
    return [MyCourseOut(**c) for c in AssignmentService(db).my_courses(user)]


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: DbSession):
    return UserOut.from_model(UserService(db).update_user(user_id, payload))


@router.post("/{user_id}/activate", response_model=UserOut)
def activate_user(user_id: int, db: DbSession):
    return UserOut.from_model(UserService(db).set_active(user_id, True))


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: int, db: DbSession):
    return UserOut.from_model(UserService(db).set_active(user_id, False))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DbSession, admin: Annotated[User, Depends(require_admin)]):
    """Permanently delete a user (and their dependent records) from the DB."""
    UserService(db).delete_user(user_id, actor=admin)
