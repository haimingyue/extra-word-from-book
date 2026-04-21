import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import app.models  # noqa: F401
from app.api.router import api_router
from app.core.config import get_settings


settings = get_settings()
logger = logging.getLogger("app")

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API for EPUB vocabulary analysis.\n\n"
        "Auth flow for Swagger:\n"
        "1. Call `POST /api/v1/auth/register` once to create an account.\n"
        "2. Call `POST /api/v1/auth/login` to get `access_token`.\n"
        "3. Click `Authorize` in the top-right corner.\n"
        "4. Paste the raw JWT token value.\n"
        "5. Call protected endpoints with the saved token."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
    },
    openapi_tags=[
        {"name": "auth", "description": "Register and login endpoints."},
        {"name": "books", "description": "Upload EPUB files and view analysis history."},
        {"name": "analysis", "description": "Create analysis jobs, query results, and download CSV files."},
        {"name": "vocabularies", "description": "Manage user-known vocabulary imports and vocabulary items."},
        {"name": "vocab-test", "description": "Estimate the user's COCA vocabulary band with a staged test."},
        {"name": "health", "description": "Service health check."},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
def on_startup() -> None:
    settings.books_storage_dir.mkdir(parents=True, exist_ok=True)
    settings.results_storage_dir.mkdir(parents=True, exist_ok=True)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request, exc: StarletteHTTPException):
    logger.warning(
        "http_exception method=%s path=%s status=%s detail=%s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(request, exc: RequestValidationError):
    logger.warning(
        "validation_exception method=%s path=%s errors=%s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Paste the JWT access token from `/api/v1/auth/login`.",
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
