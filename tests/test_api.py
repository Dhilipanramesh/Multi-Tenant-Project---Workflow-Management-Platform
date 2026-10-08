from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db() -> Generator[Session, None, None]:
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register(
    client: TestClient, email: str, username: str, organization: str
) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": username.title(),
            "password": "A-strong-password-123",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def headers(auth: dict, organization_id: int | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {auth['access_token']}"}
    if organization_id is not None:
        result["X-Organization-ID"] = str(organization_id)
    return result


def test_registration_login_and_refresh_rotation(client: TestClient) -> None:
    auth = register(client, "owner@example.com", "owner", "Acme")
    assert auth["user"]["email"] == "owner@example.com"
    login_response = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "A-strong-password-123"},
    )
    assert login_response.status_code == 200
    old_refresh = login_response.json()["refresh_token"]
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != old_refresh
    rejected = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert rejected.status_code == 401
    bad_login = client.post(
        "/api/auth/login", json={"email": "owner@example.com", "password": "wrong-password"}
    )
    assert bad_login.status_code == 401


def test_project_and_task_tenant_isolation(client: TestClient) -> None:
    first = register(client, "one@example.com", "one", "Org One")
    second = register(client, "two@example.com", "two", "Org Two")
    first_org = client.get("/api/organizations", headers=headers(first)).json()[0]["id"]
    second_org = client.get("/api/organizations", headers=headers(second)).json()[0]["id"]
    project = client.post(
        "/api/projects", headers=headers(first, first_org), json={"name": "Private project"}
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    assert client.get(
        f"/api/projects/{project_id}", headers=headers(second, second_org)
    ).status_code == 404
    task = client.post(
        f"/api/projects/{project_id}/tasks",
        headers=headers(first, first_org),
        json={"title": "First task"},
    )
    assert task.status_code == 201
    assert client.get(
        f"/api/tasks/{task.json()['id']}", headers=headers(second, second_org)
    ).status_code == 404


def test_role_and_task_transition_rules(client: TestClient) -> None:
    auth = register(client, "admin@example.com", "admin", "Workflow Co")
    organization_id = client.get("/api/organizations", headers=headers(auth)).json()[0]["id"]
    project = client.post(
        "/api/projects", headers=headers(auth, organization_id), json={"name": "Roadmap"}
    ).json()
    task_response = client.post(
        f"/api/projects/{project['id']}/tasks",
        headers=headers(auth, organization_id),
        json={"title": "Ship API", "status": "todo"},
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]
    invalid = client.patch(
        f"/api/tasks/{task_id}",
        headers=headers(auth, organization_id),
        json={"status": "done"},
    )
    assert invalid.status_code == 409
    valid = client.patch(
        f"/api/tasks/{task_id}",
        headers=headers(auth, organization_id),
        json={"status": "in_progress"},
    )
    assert valid.status_code == 200


def test_task_dependency_blocks_completion_and_rejects_cycle(client: TestClient) -> None:
    auth = register(client, "lead@example.com", "lead", "Dependency Co")
    organization_id = client.get("/api/organizations", headers=headers(auth)).json()[0]["id"]
    project = client.post(
        "/api/projects", headers=headers(auth, organization_id), json={"name": "Build"}
    ).json()
    tasks = []
    for title in ["Foundation", "Interface"]:
        response = client.post(
            f"/api/projects/{project['id']}/tasks",
            headers=headers(auth, organization_id),
            json={"title": title, "status": "todo"},
        )
        tasks.append(response.json()["id"])
    prerequisite_id, task_id = tasks
    assert client.post(
        f"/api/tasks/{task_id}/dependencies",
        headers=headers(auth, organization_id),
        json={"depends_on_id": prerequisite_id},
    ).status_code == 201
    blocked = client.patch(
        f"/api/tasks/{task_id}",
        headers=headers(auth, organization_id),
        json={"status": "in_progress"},
    )
    assert blocked.status_code == 409
    cycle = client.post(
        f"/api/tasks/{prerequisite_id}/dependencies",
        headers=headers(auth, organization_id),
        json={"depends_on_id": task_id},
    )
    assert cycle.status_code == 409


def test_comment_owner_access_and_notification_scope(client: TestClient) -> None:
    auth = register(client, "commenter@example.com", "commenter", "Comments Inc")
    organization_id = client.get("/api/organizations", headers=headers(auth)).json()[0]["id"]
    project = client.post(
        "/api/projects", headers=headers(auth, organization_id), json={"name": "Collaboration"}
    ).json()
    task = client.post(
        f"/api/projects/{project['id']}/tasks",
        headers=headers(auth, organization_id),
        json={"title": "Discuss"},
    ).json()
    comment = client.post(
        f"/api/tasks/{task['id']}/comments",
        headers=headers(auth, organization_id),
        json={"body": "Initial update"},
    )
    assert comment.status_code == 201
    assert client.patch(
        f"/api/comments/{comment.json()['id']}",
        headers={"Authorization": "Bearer invalid"},
        json={"body": "forged"},
    ).status_code == 401
    notifications = client.get("/api/notifications", headers=headers(auth, organization_id))
    assert notifications.status_code == 200


def test_pagination_and_filter_validation(client: TestClient) -> None:
    auth = register(client, "filter@example.com", "filter", "Filter Inc")
    organization_id = client.get("/api/organizations", headers=headers(auth)).json()[0]["id"]
    project = client.post(
        "/api/projects", headers=headers(auth, organization_id), json={"name": "Filters"}
    ).json()
    for title, priority in [("Payment retry", "high"), ("Account settings", "low")]:
        response = client.post(
            f"/api/projects/{project['id']}/tasks",
            headers=headers(auth, organization_id),
            json={"title": title, "priority": priority},
        )
        assert response.status_code == 201
    filtered = client.get(
        "/api/tasks?page=1&page_size=1&priority=high&search=payment",
        headers=headers(auth, organization_id),
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["title"] == "Payment retry"
    assert client.get(
        "/api/tasks?page=0", headers=headers(auth, organization_id)
    ).status_code == 422
