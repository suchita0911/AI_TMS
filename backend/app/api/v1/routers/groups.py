"""Group management endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession, require_admin
from app.models.user import Group
from app.schemas.common import Message, Page
from app.schemas.user import GroupCreate, GroupOut, GroupUpdate, UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/groups", tags=["Groups"])


def _to_out(group: Group) -> GroupOut:
    return GroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        member_count=len(group.members),
        created_at=group.created_at,
    )


@router.get("", response_model=Page[GroupOut])
def list_groups(
    db: DbSession,
    current_user: CurrentUser,
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    items, total = UserService(db).list_groups(
        query=q, offset=(page - 1) * page_size, limit=page_size
    )
    return Page[GroupOut](
        items=[_to_out(g) for g in items], total=total, page=page, page_size=page_size
    )


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_group(payload: GroupCreate, db: DbSession):
    return _to_out(UserService(db).create_group(payload))


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: int, db: DbSession, current_user: CurrentUser):
    return _to_out(UserService(db).get_group(group_id))


@router.get("/{group_id}/members", response_model=list[UserOut],
            dependencies=[Depends(require_admin)])
def group_members(group_id: int, db: DbSession):
    group = UserService(db).get_group(group_id)
    return [UserOut.from_model(u) for u in group.members]


@router.patch("/{group_id}", response_model=GroupOut,
              dependencies=[Depends(require_admin)])
def update_group(group_id: int, payload: GroupUpdate, db: DbSession):
    return _to_out(UserService(db).update_group(group_id, payload))


@router.delete("/{group_id}", response_model=Message, dependencies=[Depends(require_admin)])
def delete_group(group_id: int, db: DbSession):
    UserService(db).delete_group(group_id)
    return Message(detail="Group deleted")
