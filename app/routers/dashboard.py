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
from app.models import AuditLog, OrganizationMember, Project, ProjectMember, Task
from app.schemas import TaskRead

router = APIRouter()


@router.get("/api/dashboard")
def dashboard(member: CurrentMembership, user: AuthenticatedUser, db: DbSession) -> dict:
    project_filter = Project.organization_id == member.organization_id
    total_projects = db.scalar(select(func.count(Project.id)).where(project_filter)) or 0
    active_projects = db.scalar(select(func.count(Project.id)).where(project_filter, Project.status == "active")) or 0
    completed_projects = db.scalar(select(func.count(Project.id)).where(project_filter, Project.status == "completed")) or 0
    org_tasks = select(Task).join(Project).where(Project.organization_id == member.organization_id)
    total_tasks = db.scalar(select(func.count()).select_from(org_tasks.subquery())) or 0
    overdue = db.scalar(
        select(func.count(Task.id)).join(Project).where(
            project_filter, Task.due_date < datetime.now(timezone.utc), Task.status.not_in(["done", "cancelled"])
        )
    ) or 0
    if member.role == "organization_admin":
        users_count = db.scalar(
            select(func.count(OrganizationMember.id)).where(
                OrganizationMember.organization_id == member.organization_id
            )
        ) or 0
        active_users = db.scalar(
            select(func.count(OrganizationMember.id)).where(
                OrganizationMember.organization_id == member.organization_id,
                OrganizationMember.is_active.is_(True),
            )
        ) or 0
        return {
            "role": member.role, "total_projects": total_projects,
            "active_projects": active_projects, "completed_projects": completed_projects,
            "total_users": users_count, "active_users": active_users,
            "total_tasks": total_tasks, "overdue_tasks": overdue,
        }
    if member.role == "project_manager":
        my_projects = db.scalar(
            select(func.count(Project.id)).join(ProjectMember).where(
                project_filter, ProjectMember.user_id == user.id
            )
        ) or 0
        status_counts = dict(
            db.execute(
                select(Task.status, func.count(Task.id)).join(Project)
                .where(project_filter).group_by(Task.status)
            ).all()
        )
        return {
            "role": member.role, "my_projects": my_projects,
            "open_tasks": sum(v for k, v in status_counts.items() if k not in {"done", "cancelled"}),
            "completed_tasks": status_counts.get("done", 0), "overdue_tasks": overdue,
            "tasks_by_priority": dict(
                db.execute(
                    select(Task.priority, func.count(Task.id)).join(Project)
                    .where(project_filter).group_by(Task.priority)
                ).all()
            ),
        }
    my_tasks = list(
        db.scalars(
            select(Task).join(Project).where(
                project_filter, Task.assignee_id == user.id
            ).order_by(Task.due_date.asc().nullslast()).limit(10)
        ).all()
    )
    today = datetime.now(timezone.utc).date()
    due_today = sum(1 for task in my_tasks if task.due_date and task.due_date.date() == today)
    return {
        "role": member.role, "my_tasks": [TaskRead.model_validate(task).model_dump(mode="json") for task in my_tasks],
        "overdue_tasks": sum(
            1 for task in my_tasks if task.due_date and task.due_date < datetime.now(timezone.utc)
            and task.status not in {"done", "cancelled"}
        ),
        "tasks_due_today": due_today,
        "recently_completed_tasks": [
            TaskRead.model_validate(task).model_dump(mode="json") for task in my_tasks if task.status == "done"
        ],
    }



@router.get("/api/audit-logs")
def list_audit_logs(
    member: ManagerMembership, db: DbSession,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
) -> list[dict]:
    rows = db.scalars(
        select(AuditLog).where(AuditLog.organization_id == member.organization_id)
        .order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [
        {
            "id": row.id, "user_id": row.user_id, "action": row.action,
            "entity_type": row.entity_type, "entity_id": row.entity_id,
            "ip_address": row.ip_address, "metadata": row.metadata_json,
            "created_at": row.created_at,
        }
        for row in rows
    ]

