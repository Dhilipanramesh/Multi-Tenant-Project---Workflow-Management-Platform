from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

ProjectStatus = Literal["planning", "active", "on_hold", "completed", "archived"]
TaskStatus = Literal[
    "backlog", "todo", "in_progress", "blocked", "review", "done", "cancelled"
]
Role = Literal["organization_admin", "project_manager", "team_member", "viewer"]
Priority = Literal["low", "medium", "high", "urgent"]


class RegisterInput(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=10, max_length=128)
    organization_name: str = Field(min_length=1, max_length=160)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class RefreshInput(BaseModel):
    refresh_token: str


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    full_name: str
    is_active: bool
    is_super_admin: bool


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(TokenPair):
    user: UserRead


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class MemberRead(BaseModel):
    user_id: int
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool


class MemberCreate(BaseModel):
    email: EmailStr
    role: Role


class MemberUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: ProjectStatus = "planning"
    start_date: datetime | None = None
    due_date: datetime | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: ProjectStatus | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    owner_id: int
    name: str
    description: str | None
    status: ProjectStatus
    start_date: datetime | None
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    assignee_id: int | None = None
    priority: Priority = "medium"
    status: TaskStatus = "backlog"
    due_date: datetime | None = None
    estimated_hours: int | None = Field(default=None, ge=0)
    actual_hours: int | None = Field(default=None, ge=0)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    assignee_id: int | None = None
    priority: Priority | None = None
    status: TaskStatus | None = None
    due_date: datetime | None = None
    estimated_hours: int | None = Field(default=None, ge=0)
    actual_hours: int | None = Field(default=None, ge=0)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    assignee_id: int | None
    reporter_id: int
    priority: Priority
    status: TaskStatus
    due_date: datetime | None
    estimated_hours: int | None
    actual_hours: int | None
    created_at: datetime
    updated_at: datetime


class DependencyCreate(BaseModel):
    depends_on_id: int


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    task_id: int | None
    author_id: int
    body: str
    created_at: datetime
    updated_at: datetime


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    message: str
    entity_type: str | None
    entity_id: int | None
    is_read: bool
    created_at: datetime
