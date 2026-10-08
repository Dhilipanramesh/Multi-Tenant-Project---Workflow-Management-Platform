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
from app.models import Project, Task, TaskDependency
from app.schemas import DependencyCreate, TaskCreate, TaskRead, TaskUpdate

router = APIRouter()


@router.get("/api/tasks", response_model=list[TaskRead])
def list_tasks(
    member: CurrentMembership, db: DbSession, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), project_id: int | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None, assignee_id: int | None = None,
    search: str | None = None,
) -> list[Task]:
    query = select(Task).join(Project).where(Project.organization_id == member.organization_id)
    if project_id is not None:
        query = query.where(Task.project_id == project_id)
    if status_filter:
        query = query.where(Task.status == status_filter)
    if priority:
        query = query.where(Task.priority == priority)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    if search:
        query = query.where(or_(Task.title.ilike(f"%{search}%"), Task.description.ilike(f"%{search}%")))
    return list(
        db.scalars(query.order_by(Task.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    )



@router.post("/api/projects/{project_id}/tasks", response_model=TaskRead, status_code=201)
def create_task(
    project_id: int, payload: TaskCreate, request: Request, member: CurrentMembership,
    user: AuthenticatedUser, db: DbSession,
) -> Task:
    project = find_project(db, project_id, member.organization_id)
    if member.role not in MANAGER_ROLES:
        ensure_project_member(db, project.id, user.id)
    data = payload.model_dump()
    assignee_id = data.get("assignee_id")
    if assignee_id is not None:
        if member.role not in MANAGER_ROLES:
            raise error("ROLE_FORBIDDEN", "Only project managers can assign tasks.", 403)
        ensure_assignable(db, project, assignee_id)
    task = Task(project_id=project.id, reporter_id=user.id, **data)
    db.add(task)
    db.flush()
    audit(db, member.organization_id, user.id, "task.created", "task", task.id, request)
    if assignee_id:
        notify(db, member.organization_id, assignee_id, "task_assigned", f"Assigned task: {task.title}.", "task", task.id)
        audit(db, member.organization_id, user.id, "task.assigned", "task", task.id, request, {"assignee_id": assignee_id})
    db.commit()
    db.refresh(task)
    return task



@router.get("/api/projects/{project_id}/tasks", response_model=list[TaskRead])
def list_project_tasks(
    project_id: int, member: CurrentMembership, db: DbSession,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
) -> list[Task]:
    project = find_project(db, project_id, member.organization_id)
    return list(
        db.scalars(
            select(Task).where(Task.project_id == project.id)
            .order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
    )



@router.get("/api/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, member: CurrentMembership, db: DbSession) -> Task:
    return find_task(db, task_id, member.organization_id)



@router.patch("/api/tasks/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int, payload: TaskUpdate, request: Request, member: CurrentMembership,
    user: AuthenticatedUser, db: DbSession,
) -> Task:
    task = find_task(db, task_id, member.organization_id)
    project = task.project
    if member.role not in MANAGER_ROLES:
        ensure_project_member(db, project.id, user.id)
        if task.assignee_id != user.id and task.reporter_id != user.id:
            raise error("TASK_ACCESS_DENIED", "Only task participants may update this task.", 403)
    changes = payload.model_dump(exclude_unset=True)
    if "assignee_id" in changes and changes["assignee_id"] != task.assignee_id:
        if member.role not in MANAGER_ROLES:
            raise error("ROLE_FORBIDDEN", "Only project managers can assign tasks.", 403)
        if changes["assignee_id"] is not None:
            ensure_assignable(db, project, changes["assignee_id"])
    new_status = changes.get("status")
    if new_status and new_status != task.status:
        if new_status not in TASK_TRANSITIONS[task.status]:
            raise error("INVALID_TASK_TRANSITION", f"Cannot move task from {task.status} to {new_status}.", 409)
        if new_status in {"in_progress", "review", "done"}:
            pending = db.scalar(
                select(func.count()).select_from(TaskDependency)
                .join(Task, Task.id == TaskDependency.depends_on_id)
                .where(TaskDependency.task_id == task.id, Task.status != "done")
            )
            if pending:
                raise error("TASK_DEPENDENCIES_INCOMPLETE", "Complete prerequisite tasks before advancing this task.", 409)
    old_assignee = task.assignee_id
    old_status = task.status
    for field, value in changes.items():
        setattr(task, field, value)
    if "assignee_id" in changes and changes["assignee_id"] != old_assignee:
        audit(db, member.organization_id, user.id, "task.assigned", "task", task.id, request,
              {"from": old_assignee, "to": changes["assignee_id"]})
        if changes["assignee_id"]:
            notify(db, member.organization_id, changes["assignee_id"], "task_assigned", f"Assigned task: {task.title}.", "task", task.id)
    if new_status and new_status != old_status:
        audit(db, member.organization_id, user.id, "task.status_changed", "task", task.id, request,
              {"from": old_status, "to": new_status})
        if task.assignee_id and task.assignee_id != user.id:
            notify(db, member.organization_id, task.assignee_id, "task_status_changed", f"{task.title} moved to {new_status}.", "task", task.id)
    db.commit()
    db.refresh(task)
    return task



@router.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int, request: Request, member: ManagerMembership,
    user: AuthenticatedUser, db: DbSession,
) -> Response:
    task = find_task(db, task_id, member.organization_id)
    audit(db, member.organization_id, user.id, "task.deleted", "task", task.id, request)
    db.delete(task)
    db.commit()
    return Response(status_code=204)



@router.post("/api/tasks/{task_id}/dependencies", status_code=201)
def add_dependency(
    task_id: int, payload: DependencyCreate, request: Request,
    member: ManagerMembership, user: AuthenticatedUser, db: DbSession,
) -> dict[str, int]:
    task = find_task(db, task_id, member.organization_id)
    prerequisite = find_task(db, payload.depends_on_id, member.organization_id)
    if task.id == prerequisite.id:
        raise error("CIRCULAR_DEPENDENCY", "A task cannot depend on itself.", 409)
    if task.project_id != prerequisite.project_id:
        raise error("CROSS_PROJECT_DEPENDENCY", "Dependencies must be in the same project.", 400)
    pending = [prerequisite.id]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if current == task.id:
            raise error("CIRCULAR_DEPENDENCY", "This dependency would create a cycle.", 409)
        if current in visited:
            continue
        visited.add(current)
        pending.extend(
            db.scalars(
                select(TaskDependency.depends_on_id).where(TaskDependency.task_id == current)
            ).all()
        )
    try:
        db.add(TaskDependency(task_id=task.id, depends_on_id=prerequisite.id))
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise error("DUPLICATE_DEPENDENCY", "Dependency already exists.", 409) from exc
    audit(db, member.organization_id, user.id, "task.dependency_added", "task", task.id, request,
          {"depends_on_id": prerequisite.id})
    db.commit()
    return {"task_id": task.id, "depends_on_id": prerequisite.id}

