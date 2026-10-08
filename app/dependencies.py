from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import error
from app.core.policies import MANAGER_ROLES
from app.core.security import decode_access_token
from app.database import get_db
from app.models import AuditLog, Notification, OrganizationMember, Project, ProjectMember, Task, User

DbSession = Annotated[Session, Depends(get_db)]

def audit(
    db: Session, org_id: int, user_id: int | None, action: str,
    entity_type: str, entity_id: int | None, request: Request | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=request.client.host if request and request.client else None,
            metadata_json=metadata or {},
        )
    )


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise error("AUTHENTICATION_REQUIRED", "A bearer access token is required.", 401)
    user_id = decode_access_token(authorization.split(" ", 1)[1].strip())
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise error("INACTIVE_OR_UNKNOWN_USER", "This account cannot authenticate.", 401)
    return user


AuthenticatedUser = Annotated[User, Depends(get_current_user)]


def get_membership(
    user: AuthenticatedUser,
    db: DbSession,
    organization_id: Annotated[int | None, Header(alias="X-Organization-ID")] = None,
) -> OrganizationMember:
    query = select(OrganizationMember).where(
        OrganizationMember.user_id == user.id,
        OrganizationMember.is_active.is_(True),
    )
    if organization_id is not None:
        query = query.where(OrganizationMember.organization_id == organization_id)
    memberships = list(db.scalars(query.order_by(OrganizationMember.id)).all())
    if not memberships:
        raise error("ORGANIZATION_ACCESS_DENIED", "You do not have access to this organization.", 403)
    if organization_id is None and len(memberships) > 1:
        raise error("ORGANIZATION_REQUIRED", "Select an organization using X-Organization-ID.", 400)
    return memberships[0]


def require_manager(member: CurrentMembership) -> OrganizationMember:
    if member.role not in MANAGER_ROLES:
        raise error("ROLE_FORBIDDEN", "This action requires a manager role.", 403)
    return member


def find_project(db: Session, project_id: int, org_id: int) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id, Project.organization_id == org_id
        )
    )
    if project is None:
        raise error("PROJECT_NOT_FOUND", "You do not have access to this project.", 404)
    return project


def find_task(db: Session, task_id: int, org_id: int) -> Task:
    task = db.scalar(
        select(Task).join(Project).where(
            Task.id == task_id, Project.organization_id == org_id
        )
    )
    if task is None:
        raise error("TASK_NOT_FOUND", "You do not have access to this task.", 404)
    return task


def ensure_project_member(db: Session, project_id: int, user_id: int) -> None:
    if db.scalar(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    ) is None:
        raise error("PROJECT_MEMBERSHIP_REQUIRED", "User must belong to this project.", 400)


def ensure_assignable(db: Session, project: Project, user_id: int) -> User:
    member = db.scalar(
        select(OrganizationMember)
        .join(User)
        .where(
            OrganizationMember.organization_id == project.organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active.is_(True),
            User.is_active.is_(True),
        )
    )
    if member is None:
        raise error("ASSIGNEE_NOT_ACTIVE_MEMBER", "Assignee must be an active organization member.", 400)
    if member.role == "viewer":
        raise error("VIEWER_NOT_ASSIGNABLE", "Viewers cannot be assigned tasks.", 400)
    ensure_project_member(db, project.id, user_id)
    return member.user


def notify(
    db: Session, org_id: int, user_id: int, kind: str, message: str,
    entity_type: str | None = None, entity_id: int | None = None,
) -> None:
    db.add(
        Notification(
            organization_id=org_id,
            user_id=user_id,
            kind=kind,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    )


CurrentMembership = Annotated[OrganizationMember, Depends(get_membership)]
ManagerMembership = Annotated[OrganizationMember, Depends(require_manager)]
