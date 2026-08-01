import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.core.limiter import limiter

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
from src.modules.public.router import router as public_router
from src.modules.modules.router import router as modules_router
from src.modules.classes.router import router as classes_router
from src.modules.groups.router import router as groups_router
from src.modules.sessions.router import router as sessions_router
from src.modules.enrollments.router import enrollment_router, visitor_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(settings.APP_NAME)

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


async def expire_overdue_visitor_reservations():
    """Runs hourly to expire visitor reservations past hold_hours + 48h grace period."""
    from src.core.database import sessionmanager
    from sqlalchemy import select
    from datetime import datetime, timezone, timedelta
    from src.modules.config.models import SystemConfig
    from src.modules.enrollments.models import Enrollment
    from src.modules.enrollments.visitor_models import VisitorEnrollmentRequest
    
    async with sessionmanager.session() as db:
        config_result = await db.execute(select(SystemConfig).limit(1))
        config = config_result.scalar_one_or_none()
        hold_hours = config.enrollment_reservation_hold_hours if config else 72
        
        # Expire at hold_hours + 48h grace period
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hold_hours + 48)
        
        # Find overdue pending visitor requests
        result = await db.execute(
            select(VisitorEnrollmentRequest)
            .join(Enrollment, Enrollment.id == VisitorEnrollmentRequest.enrollment_id)
            .where(
                VisitorEnrollmentRequest.status == "pending",
                Enrollment.source == "visitor_form",
                Enrollment.created_at < cutoff
            )
        )
        overdue_reqs = result.scalars().all()
        for req in overdue_reqs:
            req.status = "rejected"
            req.notes = (req.notes or "") + "\n[Auto-expired due to no-show]"
            
            enrollment = await db.execute(select(Enrollment).where(Enrollment.id == req.enrollment_id))
            enrollment = enrollment.scalar_one()
            
            # Since it's pending visitor, it holds a seat. We must free it (cancel enrollment)
            enrollment.status = "cancelled"
            enrollment.cancelled_at = datetime.now(timezone.utc)
            enrollment.cancelled_reason = "auto_expired"
            
            # Promote next in waitlist
            from src.common.enrollment_engine import promote_next_in_waitlist
            await promote_next_in_waitlist(db, enrollment.group_id, is_manual=False)
            
        if overdue_reqs:
            await db.commit()
            logger.info(f"Auto-expired {len(overdue_reqs)} overdue visitor reservations.")



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    scheduler = AsyncIOScheduler()
    try:
        await run_migrations()
        scheduler.add_job(
            expire_overdue_visitor_reservations, 
            'interval', 
            hours=1, 
            id='expire_reservations',
            replace_existing=True
        )
        scheduler.start()
        # You can add global startup jobs here
        yield
    except Exception as exc:
        logger.critical("CRITICAL: Application failed to start: %s", exc, exc_info=True)
        raise

    scheduler.shutdown()
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

    # Rate limiting — must come after CORS
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Register your routers here
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(parent_links_router, prefix="/api")
    app.include_router(config_router, prefix="/api")
    app.include_router(branches_router, prefix="/api")
    app.include_router(notifications_router, prefix="/api")
    app.include_router(logs_router, prefix="/api")
    app.include_router(landing_router, prefix="/api")
    app.include_router(public_router, prefix="/api")
    app.include_router(modules_router, prefix="/api")
    app.include_router(classes_router, prefix="/api")
    app.include_router(groups_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(visitor_router, prefix="/api")
    app.include_router(enrollment_router, prefix="/api")

    @app.get("/health")
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
