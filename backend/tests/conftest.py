import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent

# resources.py reads data files via paths relative to the backend directory,
# and server.py builds boto3 clients at import time, so set both up before
# any application module is imported.
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DEFAULT_AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
# load_dotenv() never overrides existing vars, so these win over any local .env.
os.environ["USE_S3"] = "false"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"


@pytest.fixture
def server_module(monkeypatch, tmp_path):
    """The server module with local memory pointed at a temp dir and S3 off."""
    import server

    monkeypatch.setattr(server, "MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setattr(server, "USE_S3", False)
    return server


@pytest.fixture
def client(server_module):
    from fastapi.testclient import TestClient

    return TestClient(server_module.app)
