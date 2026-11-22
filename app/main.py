from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.api.routes.auth import router as auth_router
from app.api.routes.projects import router as projects_router
from app.core.config import Settings, get_settings
from app.db.session import create_database_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    engine = create_database_engine(app_settings.database_url)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        yield
        engine.dispose()

    application = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        description="API for automated test result ingestion and reporting.",
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(projects_router, prefix="/api/v1")

    @application.get("/health", tags=["operations"])
    def health_check() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}

    frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    frontend_index = frontend_dist / "index.html"
    if frontend_index.is_file():

        @application.get("/{path:path}", include_in_schema=False)
        def serve_frontend(path: str) -> FileResponse:
            if path == "api" or path.startswith("api/") or path == "health":
                raise HTTPException(status_code=404, detail="Not found")

            requested_file = (frontend_dist / path).resolve()
            if not requested_file.is_relative_to(frontend_dist.resolve()):
                raise HTTPException(status_code=404, detail="Not found")
            if not requested_file.is_file():
                requested_file = frontend_index
            return FileResponse(requested_file)

        @application.get("/", include_in_schema=False)
        def serve_frontend_root() -> FileResponse:
            return FileResponse(frontend_index)

    return application


app = create_app()
