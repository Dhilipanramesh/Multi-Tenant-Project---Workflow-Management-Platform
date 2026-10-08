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
from app.models import Organization, OrganizationMember, User
from app.schemas import MemberCreate, MemberRead, MemberUpdate, OrganizationCreate, OrganizationRead

router = APIRouter()


@router.get("/api/organizations", response_model=list[OrganizationRead])
def list_organizations(user: AuthenticatedUser, db: DbSession) -> list[Organization]:
    return list(
        db.scalars(
            select(Organization)
            .join(OrganizationMember)
            .where(
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active.is_(True),
            )
            .order_by(Organization.name)
        ).all()
    )



@router.post("/api/organizations", response_model=OrganizationRead, status_code=201)
def create_organization(
    payload: OrganizationCreate, request: Request, user: AuthenticatedUser, db: DbSession
) -> Organization:
    organization = Organization(name=payload.name)
    try:
        db.add(organization)
        db.flush()
        db.add(
            OrganizationMember(
                organization_id=organization.id, user_id=user.id, role="organization_admin"
            )
        )
        audit(db, organization.id, user.id, "organization.created", "organization", organization.id, request)
        db.commit()
        db.refresh(organization)
    except IntegrityError as exc:
        db.rollback()
        raise error("ORGANIZATION_NAME_EXISTS", "Organization name already exists.", 409) from exc
    return organization



@router.get("/api/organizations/{organization_id}", response_model=OrganizationRead)
def get_organization(organization_id: int, user: AuthenticatedUser, db: DbSession) -> Organization:
    organization = db.scalar(
        select(Organization)
        .join(OrganizationMember)
        .where(
            Organization.id == organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active.is_(True),
        )
    )
    if organization is None:
        raise error("ORGANIZATION_NOT_FOUND", "You do not have access to this organization.", 404)
    return organization



@router.get("/api/organizations/{organization_id}/members", response_model=list[MemberRead])
def list_members(
    organization_id: int, user: AuthenticatedUser, db: DbSession
) -> list[dict]:
    if db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active.is_(True),
        )
    ) is None:
        raise error("ORGANIZATION_ACCESS_DENIED", "You do not have access to this organization.", 403)
    rows = db.execute(
        select(User, OrganizationMember)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(User.full_name)
    ).all()
    return [
        {
            "user_id": user_row.id,
            "email": user_row.email,
            "username": user_row.username,
            "full_name": user_row.full_name,
            "role": member.role,
            "is_active": member.is_active,
        }
        for user_row, member in rows
    ]



@router.post("/api/organizations/{organization_id}/members", response_model=MemberRead, status_code=201)
def add_member(
    organization_id: int, payload: MemberCreate, request: Request,
    user: AuthenticatedUser, db: DbSession,
) -> dict:
    actor = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active.is_(True),
        )
    )
    if actor is None:
        raise error("ORGANIZATION_ACCESS_DENIED", "You do not have access to this organization.", 403)
    if actor.role != "organization_admin":
        raise error("ROLE_FORBIDDEN", "Organization admin role is required.", 403)
    target = db.scalar(select(User).where(User.email == payload.email.lower()))
    if target is None:
        raise error("USER_NOT_FOUND", "Register this user before adding them.", 404)
    member = OrganizationMember(
        organization_id=organization_id, user_id=target.id, role=payload.role
    )
    try:
        db.add(member)
        db.flush()
        audit(db, organization_id, user.id, "member.added", "user", target.id, request)
        notify(db, organization_id, target.id, "member_added", "You were added to an organization.")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error("DUPLICATE_MEMBERSHIP", "User is already a member.", 409) from exc
    return {
        "user_id": target.id,
        "email": target.email,
        "username": target.username,
        "full_name": target.full_name,
        "role": member.role,
        "is_active": member.is_active,
    }



@router.patch("/api/organizations/{organization_id}/members/{user_id}", response_model=MemberRead)
def update_member(
    organization_id: int, user_id: int, payload: MemberUpdate, request: Request,
    actor: AuthenticatedUser, db: DbSession,
) -> dict:
    admin = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == actor.id,
            OrganizationMember.role == "organization_admin",
            OrganizationMember.is_active.is_(True),
        )
    )
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if admin is None:
        raise error("ROLE_FORBIDDEN", "Organization admin role is required.", 403)
    if member is None:
        raise error("MEMBER_NOT_FOUND", "Organization member not found.", 404)
    if user_id == actor.id and payload.is_active is False:
        raise error("CANNOT_DEACTIVATE_SELF", "You cannot deactivate your own membership.", 400)
    if payload.role is not None:
        member.role = payload.role
    if payload.is_active is not None:
        member.is_active = payload.is_active
    audit(db, organization_id, actor.id, "member.updated", "user", user_id, request)
    db.commit()
    user = db.get(User, user_id)
    return {
        "user_id": user.id, "email": user.email, "username": user.username,
        "full_name": user.full_name, "role": member.role, "is_active": member.is_active,
    }



@router.delete("/api/organizations/{organization_id}/members/{user_id}", status_code=204)
def remove_member(
    organization_id: int, user_id: int, request: Request, actor: AuthenticatedUser,
    db: DbSession,
) -> Response:
    admin = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == actor.id,
            OrganizationMember.role == "organization_admin",
            OrganizationMember.is_active.is_(True),
        )
    )
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if admin is None:
        raise error("ROLE_FORBIDDEN", "Organization admin role is required.", 403)
    if member is None:
        raise error("MEMBER_NOT_FOUND", "Organization member not found.", 404)
    if user_id == actor.id:
        raise error("CANNOT_REMOVE_SELF", "You cannot remove your own membership.", 400)
    audit(db, organization_id, actor.id, "member.removed", "user", user_id, request)
    db.delete(member)
    db.commit()
    return Response(status_code=204)

