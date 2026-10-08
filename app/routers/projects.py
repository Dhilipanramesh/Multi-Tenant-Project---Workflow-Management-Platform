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
from app.models import OrganizationMember, Project, ProjectMember
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter()


@router.post("/api/projects", response_model=ProjectRead, status_code=201)
def create_project(
    payload: ProjectCreate, request: Request, member: ManagerMembership, user: AuthenticatedUser,
    db: DbSession,
) -> Project:
    project = Project(
        organization_id=member.organization_id, owner_id=user.id, **payload.model_dump()
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id))
    audit(db, member.organization_id, user.id, "project.created", "project", project.id, request)
    db.commit()
    db.refresh(project)
    return project



@router.get("/api/projects", response_model=list[ProjectRead])
def list_projects(
    member: CurrentMembership, db: DbSession, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[Project]:
    query = select(Project).where(Project.organization_id == member.organization_id)
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))
    if status_filter:
        query = query.where(Project.status == status_filter)
    return list(
        db.scalars(query.order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    )



@router.get("/api/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, member: CurrentMembership, db: DbSession) -> Project:
    return find_project(db, project_id, member.organization_id)



@router.patch("/api/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int, payload: ProjectUpdate, request: Request,
    member: ManagerMembership, user: AuthenticatedUser, db: DbSession,
) -> Project:
    project = find_project(db, project_id, member.organization_id)
    changes = payload.model_dump(exclude_unset=True)
    new_status = changes.get("status")
    if new_status and new_status != project.status and new_status not in PROJECT_TRANSITIONS[project.status]:
        raise error("INVALID_PROJECT_TRANSITION", f"Cannot move project from {project.status} to {new_status}.", 409)
    for field, value in changes.items():
        setattr(project, field, value)
    audit(db, member.organization_id, user.id, "project.updated", "project", project.id, request)
    db.commit()
    db.refresh(project)
    return project



@router.delete("/api/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int, request: Request, member: ManagerMembership, user: AuthenticatedUser,
    db: DbSession,
) -> Response:
    project = find_project(db, project_id, member.organization_id)
    audit(db, member.organization_id, user.id, "project.deleted", "project", project.id, request)
    db.delete(project)
    db.commit()
    return Response(status_code=204)



@router.post("/api/projects/{project_id}/members/{user_id}", status_code=204)
def add_project_member(
    project_id: int, user_id: int, request: Request, member: ManagerMembership,
    user: AuthenticatedUser, db: DbSession,
) -> Response:
    project = find_project(db, project_id, member.organization_id)
    if db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == member.organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active.is_(True),
        )
    ) is None:
        raise error("ORGANIZATION_ACCESS_DENIED", "Project member must belong to the organization.", 400)
    try:
        db.add(ProjectMember(project_id=project.id, user_id=user_id))
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise error("DUPLICATE_PROJECT_MEMBERSHIP", "User is already a project member.", 409) from exc
    audit(db, member.organization_id, user.id, "project.member_added", "project", project.id, request,
          {"member_id": user_id})
    notify(db, member.organization_id, user_id, "project_member_added", f"Added to project {project.name}.", "project", project.id)
    db.commit()
    return Response(status_code=204)



@router.delete("/api/projects/{project_id}/members/{user_id}", status_code=204)
def remove_project_member(
    project_id: int, user_id: int, request: Request, member: ManagerMembership,
    user: AuthenticatedUser, db: DbSession,
) -> Response:
    project = find_project(db, project_id, member.organization_id)
    project_member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user_id
        )
    )
    if project_member is None:
        raise error("PROJECT_MEMBER_NOT_FOUND", "Project member not found.", 404)
    db.delete(project_member)
    audit(db, member.organization_id, user.id, "project.member_removed", "project", project.id, request,
          {"member_id": user_id})
    db.commit()
    return Response(status_code=204)

