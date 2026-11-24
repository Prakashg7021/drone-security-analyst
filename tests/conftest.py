import pytest

from drone_security.database import initialize_database


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.sqlite"
    initialize_database(path)
    return path
