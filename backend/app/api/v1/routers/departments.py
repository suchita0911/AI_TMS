"""Department management endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession, require_admin
from app.schemas.common import Message, Page
from app.schemas.user import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=Page[DepartmentOut])
def list_departments(
    db: DbSession,
    current_user: CurrentUser,  # any authenticated user can read departments
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    items, total = UserService(db).list_departments(
        query=q, offset=(page - 1) * page_size, limit=page_size
    )
    return Page[DepartmentOut](
        items=[DepartmentOut.model_validate(d) for d in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_department(payload: DepartmentCreate, db: DbSession):
    return DepartmentOut.model_validate(UserService(db).create_department(payload))


@router.get("/{dept_id}", response_model=DepartmentOut)
def get_department(dept_id: int, db: DbSession, current_user: CurrentUser):
    return DepartmentOut.model_validate(UserService(db).get_department(dept_id))


@router.patch("/{dept_id}", response_model=DepartmentOut,
              dependencies=[Depends(require_admin)])
def update_department(dept_id: int, payload: DepartmentUpdate, db: DbSession):
    return DepartmentOut.model_validate(UserService(db).update_department(dept_id, payload))


@router.delete("/{dept_id}", response_model=Message, dependencies=[Depends(require_admin)])
def delete_department(dept_id: int, db: DbSession):
    UserService(db).delete_department(dept_id)
    return Message(detail="Department deleted")
