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
router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
