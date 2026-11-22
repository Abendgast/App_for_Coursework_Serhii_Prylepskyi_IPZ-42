import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters")
os.environ.setdefault("DATABASE_URL", "sqlite://")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.db.base import Base
    from app.main import create_app

    settings = Settings(
        _env_file=None,
        secret_key="test-secret-key-that-is-at-least-32-characters",
        database_url="sqlite://",
        app_env="test",
    )
    application = create_app(settings)
    Base.metadata.create_all(application.state.engine)

    with TestClient(application) as test_client:
        yield test_client

    application.state.engine.dispose()
