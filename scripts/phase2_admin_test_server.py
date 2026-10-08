"""Phase 2 Admin isolation harness.

The document upload/parse/review/publish services are the actual application
services and use the installed SANZO SDK. Only AI answers use a labelled TEST
provider. No normal database, paid AI, TTS or external network is permitted.
"""
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/phase2_admin_forms"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
os.environ.update(
    DATABASE_URL="sqlite:///./evidence/phase2_admin_forms/ui-test.db",
    UPLOAD_DIR="./evidence/phase2_admin_forms/ui-uploads",
    OPENAI_API_KEY="",
    AZURE_SPEECH_KEY="",
    ADMIN_PASSWORD="TEST-phase2-admin",
    STAFF_PASSWORD="TEST-phase2-staff",
    DEMO_MODE="test",
    FRONTEND_ORIGIN="http://localhost:5175",
)

from app.main import app
from public_boundary_fixtures import TestProvider

assert app.state.store.path == OUT / "ui-test.db"
assert app.state.documents.settings.upload_dir == OUT / "ui-uploads"
app.state.ai = TestProvider(app.state.store, app.state.tools)

original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex


def guard(address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("Phase 2 TEST permits loopback only; paid AI/TTS is disabled")


def connect(self, address):
    guard(address)
    return original_connect(self, address)


def connect_ex(self, address):
    guard(address)
    return original_connect_ex(self, address)


socket.socket.connect = connect
socket.socket.connect_ex = connect_ex

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
