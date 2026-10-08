from __future__ import annotations

import re
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.policies import MANAGER_ROLES
from app.dependencies import audit, notify
from app.models import Comment, Notification, OrganizationMember, Task, User

def create_comment(
    body: str, project_id: int | None, task: Task | None, member: OrganizationMember,
    user: User, request: Request, db: Session,
) -> Comment:
    comment = Comment(
        body=body, project_id=project_id, task_id=task.id if task else None, author_id=user.id
    )
    db.add(comment)
    db.flush()
    mentioned_names = set(re.findall(r"@([A-Za-z0-9_.-]+)", body))
    if mentioned_names:
        mentioned_users = db.scalars(select(User).where(User.username.in_(mentioned_names))).all()
        for mentioned in mentioned_users:
            active = db.scalar(
                select(OrganizationMember.id).where(
                    OrganizationMember.user_id == mentioned.id,
                    OrganizationMember.organization_id == member.organization_id,
                    OrganizationMember.is_active.is_(True),
                )
            )
            if active and mentioned.id != user.id:
                notify(db, member.organization_id, mentioned.id, "mention", f"{user.full_name} mentioned you.", "comment", comment.id)
    if task and task.assignee_id and task.assignee_id != user.id:
        notify(db, member.organization_id, task.assignee_id, "comment_added", f"New comment on {task.title}.", "task", task.id)
    audit(db, member.organization_id, user.id, "comment.added", "comment", comment.id, request)
    return comment

