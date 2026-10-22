import os
import tempfile
from dataclasses import replace
from pathlib import Path

# Keep test runs away from the real database file (app.main creates an app at import time).
os.environ.setdefault("DATABASE_PATH", str(Path(tempfile.mkdtemp(prefix="review-tests-")) / "import.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.integration import AgentExecutor, build_default_registry  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.monitoring_service import MonitoringService  # noqa: E402
from app.storage import Database, TraceStore  # noqa: E402


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def registry(settings):
    return build_default_registry(settings)


@pytest.fixture(scope="session")
def executor(registry):
    return AgentExecutor(registry)


@pytest.fixture()
def store(tmp_path):
    return TraceStore(Database(tmp_path / "test.db"))


@pytest.fixture()
def monitoring(executor, store, settings):
    return MonitoringService(executor, store, settings.data_dir)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    settings = replace(get_settings(), database_path=tmp_path_factory.mktemp("db") / "api.db")
    with TestClient(create_app(settings)) as c:
        yield c
