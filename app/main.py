from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.routers import auth, comments, dashboard, health, notifications, organizations, projects, tasks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Multi-Tenant Project & Workflow API",
    version="1.0.0",
    description="Tenant-isolated project and task workflow management.",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        payload = detail
    else:
        payload = {"code": "HTTP_ERROR", "message": str(detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": payload},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": exc.errors(),
            },
        },
    )


for endpoint_router in (
    health.router,
    auth.router,
    organizations.router,
    projects.router,
    tasks.router,
    comments.router,
    notifications.router,
    dashboard.router,
):
    app.include_router(endpoint_router)
