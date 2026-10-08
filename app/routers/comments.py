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
from app.models import Comment
from app.schemas import CommentCreate, CommentRead, CommentUpdate

router = APIRouter()


@router.post("/api/tasks/{task_id}/comments", response_model=CommentRead, status_code=201)
def add_task_comment(
    task_id: int, payload: CommentCreate, request: Request, member: CurrentMembership,
    user: AuthenticatedUser, db: DbSession,
) -> Comment:
    task = find_task(db, task_id, member.organization_id)
    ensure_project_member(db, task.project_id, user.id)
    comment = create_comment(payload.body, None, task, member, user, request, db)
    db.commit()
    db.refresh(comment)
    return comment



@router.post("/api/projects/{project_id}/comments", response_model=CommentRead, status_code=201)
def add_project_comment(
    project_id: int, payload: CommentCreate, request: Request, member: CurrentMembership,
    user: AuthenticatedUser, db: DbSession,
) -> Comment:
    project = find_project(db, project_id, member.organization_id)
    ensure_project_member(db, project.id, user.id)
    comment = create_comment(payload.body, project.id, None, member, user, request, db)
    db.commit()
    db.refresh(comment)
    return comment



@router.get("/api/tasks/{task_id}/comments", response_model=list[CommentRead])
def list_task_comments(task_id: int, member: CurrentMembership, db: DbSession) -> list[Comment]:
    task = find_task(db, task_id, member.organization_id)
    return list(db.scalars(select(Comment).where(Comment.task_id == task.id).order_by(Comment.created_at)).all())



@router.get("/api/projects/{project_id}/comments", response_model=list[CommentRead])
def list_project_comments(project_id: int, member: CurrentMembership, db: DbSession) -> list[Comment]:
    project = find_project(db, project_id, member.organization_id)
    return list(db.scalars(select(Comment).where(Comment.project_id == project.id).order_by(Comment.created_at)).all())



@router.patch("/api/comments/{comment_id}", response_model=CommentRead)
def update_comment(
    comment_id: int, payload: CommentUpdate, member: CurrentMembership,
    user: AuthenticatedUser, db: DbSession,
) -> Comment:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise error("COMMENT_NOT_FOUND", "Comment not found.", 404)
    if comment.author_id != user.id:
        raise error("COMMENT_EDIT_FORBIDDEN", "You may only edit your own comments.", 403)
    if comment.project_id:
        find_project(db, comment.project_id, member.organization_id)
    else:
        find_task(db, comment.task_id, member.organization_id)
    comment.body = payload.body
    db.commit()
    db.refresh(comment)
    return comment



@router.delete("/api/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int, member: CurrentMembership, user: AuthenticatedUser, db: DbSession,
) -> Response:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise error("COMMENT_NOT_FOUND", "Comment not found.", 404)
    if comment.author_id != user.id:
        raise error("COMMENT_DELETE_FORBIDDEN", "You may only delete your own comments.", 403)
    if comment.project_id:
        find_project(db, comment.project_id, member.organization_id)
    else:
        find_task(db, comment.task_id, member.organization_id)
    db.delete(comment)
    db.commit()
    return Response(status_code=204)

