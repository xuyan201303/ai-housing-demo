"""Persistent, initially empty Phase 2 final acceptance environment.

Uploads, SDK parses, confirmations and publications must happen in Chrome.
This harness does not seed data. TEST responses exercise the installed business
Tools and permission gates; they are not AI or Japanese-voice acceptance.
"""
import hashlib
import json
import os
import re
import secrets
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/phase2_admin_e2e"
OUT.mkdir(parents=True, exist_ok=True)
CREDENTIALS = OUT / "credentials.json"
if not CREDENTIALS.exists():
    fd = os.open(CREDENTIALS, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump({"admin": secrets.token_urlsafe(18), "staff": secrets.token_urlsafe(18)}, stream)
credentials = json.loads(CREDENTIALS.read_text())
os.chmod(CREDENTIALS, 0o600)
sys.path.insert(0, str(ROOT / "backend"))
os.environ.update(
    DATABASE_URL="sqlite:///./evidence/phase2_admin_e2e/ui-test.db",
    UPLOAD_DIR="./evidence/phase2_admin_e2e/ui-uploads",
    OPENAI_API_KEY="",
    AZURE_SPEECH_KEY="",
    ADMIN_PASSWORD=credentials["admin"],
    STAFF_PASSWORD=credentials["staff"],
    DEMO_MODE="test",
    FRONTEND_ORIGIN="http://localhost:5177",
    VOICE_OUTPUT_PROVIDER="azure_tts",
    AZURE_SPEECH_VOICE="ja-JP-NanamiNeural",
    AZURE_SPEECH_STYLE="chat",
    AZURE_SPEECH_RATE="+15%",
    AZURE_SPEECH_STYLEDEGREE="1.15",
)
# Prevent even a read of the normal .env. All configuration above is TEST-only.
import dotenv
dotenv.load_dotenv = lambda *args, **kwargs: False

from app.main import app
from app.models.domain import now
from app.services.context import observe_customer, snapshot_for, selected
from app.services.guardrails import needs_loan_handoff, HANDOFF_MESSAGE
from app.services.knowledge_access import evidence_revision

assert app.state.store.path == OUT / "ui-test.db"
assert app.state.documents.settings.upload_dir == OUT / "ui-uploads"
assert not app.state.documents.settings.api_key
assert not app.state.documents.settings.azure_speech_key


class AdminAcceptanceTestProvider:
    """Deterministic routing; every displayed fact comes from the real Tools."""

    def __init__(self, store, tools):
        self.store, self.tools = store, tools

    async def respond(self, record, question):
        evidence_revision(self.store, record)
        self.store.event(record["id"], "message", {
            "role": "user", "text": question, "channel": "text", "created_at": now(),
        })
        record = observe_customer(self.store, record, question)
        snapshot = snapshot_for(self.store, record)
        has_property = bool(selected(record, snapshot))
        calls = []
        references = []

        def tool(name, arguments):
            result = self.tools.execute(record, name, arguments)
            calls.append({"name": name, "result": result})
            references.extend(result.get("references", []))
            return result

        if needs_loan_handoff(question):
            result = tool("call_staff", {"reason": "住宅ローン審査の判断依頼", "last_customer_question": question})
            answer = HANDOFF_MESSAGE
        elif re.search(r"紹介|見(?:られる|れる|たい).*物件|物件.*(?:見たい|あります)", question):
            result = tool("list_properties", {})
            names = [item["property_name"] for item in result.get("properties", [])]
            answer = "公開済みのサンプル物件：" + "、".join(names) if names else "この接客版に公開済みの物件はありません。"
        elif re.search(r"ローン|金利|借入|返済|フラット", question):
            result = tool("get_mortgage_rates", {})
            products = []
            for rate in result.get("rates", []):
                conditions = list(rate.get("conditions", []))
                if rate.get("notes"):
                    conditions.append(str(rate["notes"]))
                products.append(f"{rate.get('bank', '')} {rate.get('product', '')}：参考金利 {rate.get('rate')}%。基準日 {rate.get('effective_date')}。条件：" + "／".join(conditions))
            answer = "\n".join(products) + "\n商品を選択し、画面の試算フォームで条件を入力してください。計算は実際のBackendで行います。"
        elif re.search(r"価格|値段|いくら|設備|面積|間取り|最寄|駅|徒歩|物件概要|概要", question):
            if not has_property:
                answer = "どの物件についてのご質問ですか？物件を紹介できます。"
            else:
                result = tool("get_property_overview", {})
                prop = result.get("property", {})
                if "設備" in question:
                    answer = "登録設備：" + "／".join(str(value) for value in prop.get("equipment", []))
                elif re.search(r"価格|値段|いくら", question):
                    price = prop.get("price")
                    answer = f"この接客版の登録価格は {price:,} 円です。" if price is not None else "この接客版の資料に価格は登録されていません。"
                else:
                    facts = [("物件名", "property_name"), ("間取り", "layout"), ("土地面積", "land_area"), ("建物面積", "building_area"), ("最寄駅", "station"), ("徒歩分数", "walking_minutes")]
                    answer = "\n".join(f"{label}：{prop[key]}" for label, key in facts if prop.get(key) is not None)
        else:
            if has_property:
                result = tool("search_property_knowledge", {"query": question})
            else:
                result = tool("search_consultation_knowledge", {"query": question, "scope": "general"})
            texts = [str(item["text"]) for item in result.get("items", []) if item.get("text")]
            answer = "\n\n".join(texts[:3]) if texts else "この接客版の確認・公開済み資料に、質問に対応する記載はありません。担当スタッフに確認できます。"

        answer = "TEST provider（実資料・Tools確認）\n" + answer
        self.store.event(record["id"], "message", {
            "role": "assistant", "text": answer, "channel": "text", "created_at": now(),
            "references": references, "tool_results": calls, "provider": "TEST",
        })
        return {"answer": answer, "references": references, "tool_results": calls,
                "provider": "TEST", "version": record["version"]}


app.state.ai = AdminAcceptanceTestProvider(app.state.store, app.state.tools)


@app.middleware("http")
async def isolation_identity(request, call_next):
    response = await call_next(request)
    response.headers["X-SANZO-Test-Harness"] = "phase2_admin_e2e"
    return response


original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex


def guard(address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("Phase 2 Admin E2E TEST permits loopback only; paid AI/TTS is disabled")


def connect(self, address):
    guard(address)
    return original_connect(self, address)


def connect_ex(self, address):
    guard(address)
    return original_connect_ex(self, address)


socket.socket.connect = connect
socket.socket.connect_ex = connect_ex

sources = sorted((ROOT / "backend/app").rglob("*.py")) + sorted((ROOT / "frontend/src").glob("*"))
code_hash = hashlib.sha256()
for path in sources:
    if path.is_file():
        code_hash.update(str(path.relative_to(ROOT)).encode())
        code_hash.update(path.read_bytes())
(OUT / "runtime.json").write_text(json.dumps({
    "harness": "phase2_admin_e2e", "database": str(app.state.store.path),
    "upload_dir": str(app.state.documents.settings.upload_dir), "backend": "http://127.0.0.1:8004",
    "frontend": "http://localhost:5177", "frontend_proxy": "http://127.0.0.1:8004",
    "demo_mode": "test", "sdk_version": app.state.documents.adapter.sdk_version,
    "ai_credentials_configured": False, "azure_credentials_configured": False,
    "external_connections_allowed": False, "provider": "TEST - actual business Tools",
    "seeded_documents": False, "code_sha256_at_start": code_hash.hexdigest(),
}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004, log_level="warning")
