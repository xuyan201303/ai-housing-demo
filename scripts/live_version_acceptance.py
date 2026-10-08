"""Scenario B with real SDK parsing and real AiService on a private test DB.

This is local-service execution, not an HTTP/browser test. The updated price is
an explicitly synthetic TEST fixture, never an official market price update.
No main/test HTTP instance database is accessed. Two customer turns maximum.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "evidence/live_version"
OUTPUT = ROOT / "evidence/live_version_acceptance.json"


def hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def safe(value):
    if isinstance(value, dict):
        return {k: safe(v) for k, v in value.items() if k not in {"token", "api_key", "password", "authorization"}}
    if isinstance(value, list):
        return [safe(v) for v in value]
    return value


def generate_test_pdf(path):
    pdfmetrics.registerFont(TTFont("ScenarioBJP", str(ROOT / "assets/fonts/NotoSansJP-Regular.ttf")))
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setTitle("TEST ONLY - synthetic price update for Scenario B")
    pdf.setAuthor("SANZO isolated acceptance")
    pdf.setFont("ScenarioBJP", 15)
    pdf.drawString(42, 800, "TEST ONLY - Scenario B 価格更新検証")
    pdf.setFont("ScenarioBJP", 9)
    lines = [
        "この資料は隔離テスト専用です。公式の販売価格更新ではありません。",
        "property_name: TEST ONLY - version update fixture",
        "lot: No.15 TEST",
        "price: 77000000",
        "source_name: SANZO generated TEST ONLY version-update fixture",
        "source_url: https://example.invalid/scenario-b-test-price-update",
        "checked_at: 2026-10-07",
        "effective_date: 2026-10-07",
        "valid_until: 2026-10-15",
        "scope_notes: TEST専用の合成価格77000000円。公式価格を変更する資料ではありません。",
        "元資料の物件は隔離版1に残します。正式DemoのDB・公開版を変更しません。",
    ]
    for index, line in enumerate(lines):
        pdf.drawString(42, 762 - index * 30, line)
    pdf.setFont("ScenarioBJP", 8)
    pdf.drawString(42, 35, "SANZO generated synthetic TEST source - not a developer official document")
    pdf.save()


async def main():
    if OUTPUT.exists() or (DIRECTORY / "test.db").exists():
        raise RuntimeError("Existing independent version evidence must not be overwritten")
    os.environ["DATABASE_URL"] = "sqlite:///./evidence/live_version/test.db"
    os.environ["UPLOAD_DIR"] = "./evidence/live_version/uploads"
    os.environ["DEMO_MODE"] = "test"
    # app.config loads the existing .env key/model without displaying either.
    from app.config import Settings
    from app.models.domain import AppError
    from app.repositories.store import Store
    from app.services.documents import DocumentService
    from app.services.sessions import SessionService
    from app.services.tools import ToolService
    from app.services.ai import AiService

    settings = Settings()
    assert settings.demo_mode == "test" and settings.api_key
    assert settings.database == DIRECTORY / "test.db"
    store = Store(settings.database)
    store.init()
    documents = DocumentService(store, settings)
    sessions = SessionService(store)
    ai = AiService(store, ToolService(store), settings)
    evidence = {
        "mode": "isolated_local_service_real_sdk_and_openai_not_http",
        "database": str(settings.database.relative_to(ROOT)),
        "sdk_version": documents.adapter.sdk_version,
        "customer_turn_limit": 2,
        "upstream_retry_count": 0,
        "model_override": False,
        "synthetic_updated_price": True,
        "updated_price_is_official_market_update": False,
        "documents": [],
        "sessions": [],
        "checks": {},
    }
    def save():
        OUTPUT.write_text(json.dumps(safe(evidence), ensure_ascii=False, indent=2))
    def parse_confirm_publish(path, label):
        uploaded = documents.upload(path.name, path.read_bytes())
        parsed = documents.parse(uploaded["id"])
        raw_path = DIRECTORY / (label + "_sdk_raw.json")
        raw_path.write_text(json.dumps(parsed["raw"], ensure_ascii=False, indent=2))
        confirmed = documents.confirm(uploaded["id"], parsed["normalized"], "TEST isolated Scenario B confirmation of actual SDK-parsed source; not human approval or production publication")
        published = documents.publish([uploaded["id"]])
        evidence["documents"].append({
            "label": label, "document_id": uploaded["id"], "filename": path.name,
            "source_sha256": uploaded["sha256"], "raw_sha256": hash_json(parsed["raw"]),
            "raw_path": str(raw_path.relative_to(ROOT)), "sdk_api": parsed["sdk_api"],
            "normalized_price": parsed["normalized"]["property"]["price"],
            "confirmation_note": confirmed["confirmation_note"], "published_version": published["version"],
        })
        save()
        return published

    original = ROOT / "demo_documents/物件概要_demo.pdf"
    old_version = parse_confirm_publish(original, "original")
    assert old_version["property"]["price"] == 76_900_000
    old_session = sessions.start("text")
    updated = DIRECTORY / "価格更新_TEST_ONLY.pdf"
    generate_test_pdf(updated)
    new_version = parse_confirm_publish(updated, "updated_test")
    assert new_version["property"]["price"] == 77_000_000
    new_session = sessions.start("text")
    evidence["snapshots"] = [old_version, new_version]
    save()
    for label, session in [("old_after_new_publication", old_session), ("new_after_new_publication", new_session)]:
        record = {"label": label, "session_id": session["id"], "version": session["version"], "question": "この接客で公開されている物件の販売価格は何円ですか？"}
        evidence["sessions"].append(record)
        save()
        try:
            record["response"] = await ai.respond(session, record["question"])
        except AppError as exc:
            record["error"] = {"code": exc.code, "message": exc.message, "status": exc.status}
            evidence["status"] = "ACTUAL_ERROR_RECORDED_NO_RETRY"
            save()
            break
        record["persisted_view"] = sessions.view(session)
        record["ended_view"] = sessions.end(session)
        save()
    checks = evidence["checks"]
    checks["actual_sdk_prices_changed"] = old_version["property"]["price"] == 76_900_000 and new_version["property"]["price"] == 77_000_000
    checks["separate_immutable_versions"] = old_version["version"] != new_version["version"] and store.version(old_version["version"])["property"]["price"] == 76_900_000
    checks["old_session_stays_old_snapshot"] = sessions.view(old_session)["snapshot"]["property"]["price"] == 76_900_000
    checks["new_session_uses_new_snapshot"] = sessions.view(new_session)["snapshot"]["property"]["price"] == 77_000_000
    checks["two_real_openai_answers"] = len(evidence["sessions"]) == 2 and all(s.get("response", {}).get("provider") == "openai" for s in evidence["sessions"])
    if checks["two_real_openai_answers"]:
        old_record, new_record = evidence["sessions"]
        old_answer = old_record["response"]["answer"].replace(",", "").replace(" ", "")
        new_answer = new_record["response"]["answer"].replace(",", "").replace(" ", "")
        checks["old_answer_price"] = ("76900000" in old_answer or "7690万円" in old_answer) and "77000000" not in old_answer
        checks["new_answer_price"] = ("77000000" in new_answer or "7700万円" in new_answer) and "76900000" not in new_answer
        checks["answer_versions_pinned"] = all(s["response"]["version"] == s["version"] for s in evidence["sessions"])
        checks["references_never_cross_versions"] = all(all(r["document_id"] in store.version(s["version"])["document_ids"] for r in s["response"]["references"]) for s in evidence["sessions"])
        checks["session_history_isolated"] = all(len(s["persisted_view"]["messages"]) == 2 and all(m.get("version", s["version"]) == s["version"] for m in s["persisted_view"]["messages"]) for s in evidence["sessions"])
    evidence.setdefault("status", "PASS" if all(checks.values()) else "REQUIRES_SEMANTIC_REVIEW")
    save()
    print(json.dumps({"status": evidence["status"], "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
