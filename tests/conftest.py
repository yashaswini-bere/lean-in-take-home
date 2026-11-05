import os
import tempfile
from pathlib import Path

import pytest

_db = Path(tempfile.mkdtemp()) / "test.db"
os.environ["CIRCLES_DB"] = str(_db)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="session")
def client():
    seed()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def get(client):
    def _get(user_id, **params):
        response = client.get(f"/users/{user_id}/recommendations", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    return _get
