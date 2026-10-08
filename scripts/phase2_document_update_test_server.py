"""Phase 2 round 2 isolation harness; actual document SDK, TEST answers only.

The normal database is never opened. SDK parsing, manual confirmations, draft
publication, mortgage and Staff use the actual application services. External
connections are blocked; OpenAI/Azure credentials are blank in this process.
"""
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/phase2_document_update"
sys.path.insert(0, str(ROOT / "backend"))
os.environ.update(
    DATABASE_URL="sqlite:///./evidence/phase2_document_update/ui-test.db",
    UPLOAD_DIR="./evidence/phase2_document_update/ui-uploads",
    OPENAI_API_KEY="",
    AZURE_SPEECH_KEY="",
    ADMIN_PASSWORD="TEST-phase2-update-admin",
    STAFF_PASSWORD="TEST-phase2-update-staff",
    DEMO_MODE="test",
    FRONTEND_ORIGIN="http://localhost:5176",
)

from app.main import app
from app.models.domain import now
from app.services.context import observe_customer

assert app.state.store.path == OUT / "ui-test.db"
assert app.state.documents.settings.upload_dir == OUT / "ui-uploads"


class UpdateTestProvider:
    """Labelled deterministic exercise of real Tools, not AI/voice acceptance."""
    def __init__(self, store, tools):
        self.store, self.tools = store, tools

    async def respond(self, record, question):
        self.store.event(record["id"], "message", {
            "role": "user", "text": question, "channel": "text", "created_at": now(),
        })
        record = observe_customer(self.store, record, question)
        if "紹介" in question:
            name, arguments = "list_properties", {}
            answer = "TEST: この接客版に登録されているサンプルです。"
        elif "価格" in question or "設備" in question:
            name, arguments = "get_property_overview", {}
            answer = None
        elif "ローン" in question:
            name, arguments = "get_mortgage_rates", {}
            answer = "TEST: 公開済みの参考金利と条件を確認し、商品を選択してください。"
        else:
            name, arguments = "search_consultation_knowledge", {"query": "住宅購入", "scope": "general"}
            answer = "TEST: 確認・公開済みの住宅購入資料を表示します。"
        result = self.tools.execute(record, name, arguments)
        if answer is None:
            price = result.get("property", {}).get("price")
            answer = f"TEST: この接客版の登録価格は {price:,} 円です。資料カードでご確認ください。" if price is not None else "TEST: 資料カードを確認してください。"
        references = result.get("references", [])
        tools = [{"name": name, "result": result}]
        self.store.event(record["id"], "message", {
            "role": "assistant", "text": answer, "channel": "text", "created_at": now(),
            "references": references, "tool_results": tools,
        })
        return {"answer": answer, "references": references, "tool_results": tools, "version": record["version"]}


app.state.ai = UpdateTestProvider(app.state.store, app.state.tools)
original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex


def guard(address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("Phase 2 update TEST permits loopback only; paid AI/TTS is disabled")


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
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="warning")
