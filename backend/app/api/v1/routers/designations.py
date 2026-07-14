"""Job-designation catalogue endpoints.

A lightweight list of known job titles used by the employee forms and the AI
course-recommendation picker. Any authenticated user can read it; admins can add
new designations on the fly (they appear immediately in every picker)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, require_admin
from app.schemas.user import DesignationCreate, DesignationOut
from app.services.user_service import UserService

router = APIRouter(prefix="/designations", tags=["Designations"])


@router.get("", response_model=list[DesignationOut])
def list_designations(db: DbSession, current_user: CurrentUser):
    return [DesignationOut.model_validate(d) for d in UserService(db).list_designations()]


@router.post("", response_model=DesignationOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_designation(payload: DesignationCreate, db: DbSession):
    return DesignationOut.model_validate(UserService(db).create_designation(payload))
