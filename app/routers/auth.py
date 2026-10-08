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
from app.models import Organization, OrganizationMember, RefreshToken, User
from app.schemas import AuthResponse, ChangePasswordInput, LoginInput, RefreshInput, RegisterInput, TokenPair, UserRead

router = APIRouter()


@router.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterInput, request: Request, db: DbSession) -> AuthResponse:
    user = User(
        email=payload.email.lower(),
        username=payload.username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    organization = Organization(name=payload.organization_name)
    try:
        db.add_all([user, organization])
        db.flush()
        member = OrganizationMember(
            user_id=user.id, organization_id=organization.id, role="organization_admin"
        )
        db.add(member)
        db.flush()
        audit(db, organization.id, user.id, "user.registered", "user", user.id, request)
        token_pair = issue_tokens(db, user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise error("DUPLICATE_ACCOUNT_OR_ORGANIZATION", "Email, username, or organization already exists.", 409) from exc
    return AuthResponse(**token_pair.model_dump(), user=user)



@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginInput, request: Request, db: DbSession) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise error("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active.is_(True),
        ).order_by(OrganizationMember.id)
    )
    if membership:
        audit(db, membership.organization_id, user.id, "auth.login", "user", user.id, request)
    token_pair = issue_tokens(db, user)
    db.commit()
    return AuthResponse(**token_pair.model_dump(), user=user)



@router.post("/api/auth/refresh", response_model=TokenPair)
def refresh_tokens(payload: RefreshInput, db: DbSession) -> TokenPair:
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    if record is None:
        raise error("INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired.", 401)
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise error("INACTIVE_OR_UNKNOWN_USER", "This account cannot authenticate.", 401)
    record.revoked_at = datetime.now(timezone.utc)
    tokens = issue_tokens(db, user)
    db.commit()
    return tokens



@router.post("/api/auth/logout", status_code=204)
def logout(payload: RefreshInput, db: DbSession) -> Response:
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return Response(status_code=204)



@router.get("/api/auth/me", response_model=UserRead)
def me(user: AuthenticatedUser) -> User:
    return user



@router.post("/api/auth/change-password", status_code=204)
def change_password(payload: ChangePasswordInput, user: AuthenticatedUser, db: DbSession) -> Response:
    if not verify_password(payload.current_password, user.password_hash):
        raise error("INVALID_CURRENT_PASSWORD", "Current password is incorrect.", 400)
    user.password_hash = hash_password(payload.new_password)
    now = datetime.now(timezone.utc)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
    ).update({RefreshToken.revoked_at: now})
    db.commit()
    return Response(status_code=204)

