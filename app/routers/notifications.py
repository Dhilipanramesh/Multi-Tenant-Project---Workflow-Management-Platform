from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.errors import error
from app.core.policies import MANAGER_ROLES, PROJECT_TRANSITIONS, TASK_TRANSITIONS
from app.core.security import hash_password, issue_tokens, verify_password
from app.dependencies import (
    AuthenticatedUser,
    CurrentMembership,
    DbSession,
    ManagerMembership,
    audit,
    ensure_assignable,
    ensure_project_member,
    find_project,
    find_task,
    notify,
)
from app.services.comments import create_comment
from app.models import Notification
from app.schemas import NotificationRead

router = APIRouter()


@router.get("/api/notifications", response_model=list[NotificationRead])
def list_notifications(
    member: CurrentMembership, user: AuthenticatedUser, db: DbSession,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification).where(
                Notification.organization_id == member.organization_id,
                Notification.user_id == user.id,
            ).order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        ).all()
    )



@router.patch("/api/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int, member: CurrentMembership, user: AuthenticatedUser, db: DbSession,
) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == member.organization_id,
            Notification.user_id == user.id,
        )
    )
    if notification is None:
        raise error("NOTIFICATION_NOT_FOUND", "Notification not found.", 404)
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification



@router.patch("/api/notifications/read-all", status_code=204)
def mark_all_notifications_read(
    member: CurrentMembership, user: AuthenticatedUser, db: DbSession,
) -> Response:
    db.query(Notification).filter(
        Notification.organization_id == member.organization_id,
        Notification.user_id == user.id,
        Notification.is_read.is_(False),
    ).update({Notification.is_read: True})
    db.commit()
    return Response(status_code=204)

