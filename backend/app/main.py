"""FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.bootstrap import init_db
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.APP_ENV)
    try:
        init_db()
    except Exception:  # pragma: no cover - startup diagnostics
        logger.exception("Database initialisation failed")
        raise

    reminder_task: asyncio.Task | None = None
    if settings.REMINDER_SCHEDULER_ENABLED:
        from app.core.scheduler import reminder_loop
        reminder_task = asyncio.create_task(reminder_loop())

    yield

    if reminder_task:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="AI Powered Training Management System — REST API",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----------------------- Exception handlers ----------------------- #
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError):
        # jsonable_encoder strips non-serialisable ctx (e.g. raw ValueError from
        # custom validators) so the error body itself never triggers a 500.
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})

    # --------------------------- Routers ------------------------------ #
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["Health"])
    def health():
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}

    return app


app = create_app()
