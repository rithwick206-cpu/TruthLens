from __future__ import annotations

import os
import tempfile
from pathlib import Path
import pytest
from backend.db import init_db


@pytest.fixture(scope="session", autouse=True)
def isolated_test_db():
    """Isolates all pytest database operations to a temporary SQLite file,
    ensuring automated test runs never pollute the live production backend/truthlens.db."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        temp_db_path = tmp_db.name

    os.environ["TRUTHLENS_DB_PATH"] = temp_db_path
    init_db(temp_db_path)

    yield temp_db_path

    try:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
    except OSError:
        pass
