import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from src.core.config import settings
from src.core.database import sessionmanager
from src.core.exceptions import AppException
from src.modules.auth.router import router as auth_router
from src.modules.users.router import router as users_router
from src.modules.users.router import parent_links_router
from src.modules.config.router import router as config_router
from src.modules.branches.router import router as branches_router
from src.modules.notifications.router import router as notifications_router
from src.modules.audit.router import router as logs_router
from src.modules.landing.router import router as landing_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(settings.APP_NAME)

async def run_migrations() -> None:
    """Run Alembic migrations in a thread so we don't block the event loop."""
    import asyncio

    def _upgrade():
        try:
            from alembic.config import Config
            from alembic import command
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations applied successfully.")
        except Exception as e:
            logger.error("Database migrations failed: %s", str(e))
            raise

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _upgrade)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    try:
        await run_migrations()
        # You can add global startup jobs here
        yield
    except Exception as exc:
        logger.critical("CRITICAL: Application failed to start: %s", exc, exc_info=True)
        raise

    await sessionmanager.close()
    logger.info("Application shutdown: database closed.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=settings.APP_NAME,
            version=settings.APP_VERSION,
            routes=app.routes,
        )
        openapi_schema.setdefault("components", {})["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
        for path in openapi_schema.get("paths", {}).values():
            for method in path.values():
                method["security"] = [{"BearerAuth": []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.FRONTEND_URL,
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register your routers here
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(parent_links_router, prefix="/api")
    app.include_router(config_router, prefix="/api")
    app.include_router(branches_router, prefix="/api")
    app.include_router(notifications_router, prefix="/api")
    app.include_router(logs_router, prefix="/api")
    app.include_router(landing_router, prefix="/api")

    @app.api_route("/health", methods=["GET", "HEAD"])
    async def health_check():
        return {"status": "ok"}

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        body: dict = {
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        }
        if exc.details:
            body["error"]["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=body)

    return app

app = create_app()
