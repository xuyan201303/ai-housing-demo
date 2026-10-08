"""SDK-backed regressions for findings from the independent core review."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.domain import AppError
from app.repositories.store import Store
from app.services.documents import DocumentService
from app.services.sessions import SessionService
from app.services.tools import ToolService

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def reviewed_system(tmp_path, monkeypatch):
    clock = {"today": "2026-10-07"}
    for module in ["app.services.documents", "app.services.sessions", "app.services.tools"]:
        monkeypatch.setattr(f"{module}.now", lambda: clock["today"] + "T12:00:00+09:00")
    store = Store(tmp_path / "review.db")
    store.init()
    documents = DocumentService(store, SimpleNamespace(upload_dir=tmp_path / "uploads", max_upload_bytes=10 * 1024 * 1024))
    return store, documents, SessionService(store), ToolService(store), clock


def parsed(documents, filename):
    target = ROOT / "demo_documents" / filename
    return documents.parse(documents.upload(target.name, target.read_bytes())["id"])


def confirmed(documents, filename, expiry):
    record = parsed(documents, filename)
    review = copy.deepcopy(record["normalized"])
    review["property"]["valid_until"] = expiry
    documents.confirm(record["id"], review, "Isolated regression: check document-specific expiry", usage='customer')
    return record


def test_expired_price_source_cannot_be_renewed_by_newer_equipment(reviewed_system):
    store, documents, sessions, _, _ = reviewed_system
    old_price = confirmed(documents, "物件概要_demo.pdf", "2020-01-01")
    equipment = confirmed(documents, "設備仕様_demo.pdf", "2030-12-31")
    with pytest.raises(AppError) as rejected:
        documents.publish([old_price["id"], equipment["id"]])
    assert rejected.value.code == "DOCUMENT_EXPIRED"
    assert store.versions() == []
    assert all(store.get("documents", r["id"])["status"] == "confirmed" for r in [old_price, equipment])
    with pytest.raises(AppError) as no_session:
        sessions.start("text", "No.15")
    assert no_session.value.code == "NO_PUBLISHED_DATA"


def test_snapshot_keeps_earliest_source_deadline_and_blocks_later_use(reviewed_system):
    _, documents, sessions, tools, clock = reviewed_system
    overview = confirmed(documents, "物件概要_demo.pdf", "2026-10-10")
    equipment = confirmed(documents, "設備仕様_demo.pdf", "2026-10-15")
    snapshot = documents.publish([overview["id"], equipment["id"]])
    assert snapshot["property"]["valid_until"] == "2026-10-10"
    assert snapshot["document_validity"][overview["id"]]["valid_until"] == "2026-10-10"
    assert snapshot["document_validity"][equipment["id"]]["valid_until"] == "2026-10-15"
    session = sessions.start("text", "No.15")
    assert tools.execute(session, "get_property_overview", {})["property"]["price"] == 76900000
    clock["today"] = "2026-10-11"
    with pytest.raises(AppError) as new_session:
        sessions.start("text", "No.15")
    assert new_session.value.code == "PROPERTY_EXPIRED"
    for tool, arguments in [("get_property_overview", {}), ("search_property_knowledge", {"query": "価格"})]:
        with pytest.raises(AppError) as continued_session:
            tools.execute(session, tool, arguments)
        assert continued_session.value.code == "PROPERTY_EXPIRED"
    call = tools.execute(session, "call_staff", {"reason": "期限切れ資料の確認", "last_customer_question": "現在の価格は？"})
    assert call["status"] == "pending"


def test_future_effective_source_cannot_publish(reviewed_system):
    store, documents, _, _, _ = reviewed_system
    record = parsed(documents, "物件概要_demo.pdf")
    review = copy.deepcopy(record["normalized"])
    review["property"]["effective_date"] = "2026-10-08"
    documents.confirm(record["id"], review, "Isolated regression: future source date", usage='customer')
    with pytest.raises(AppError) as rejected:
        documents.publish([record["id"]])
    assert rejected.value.code == "DOCUMENT_NOT_YET_EFFECTIVE"
    assert store.versions() == []


@pytest.mark.parametrize("key,value", [
    ("property_name", {"unexpected": "object"}),
    ("station", ["unexpected", "array"]),
    ("source_url", {"unexpected": "object"}),
    ("equipment", ["正しい文字列", {"unexpected": "object"}]),
    ("surroundings", "配列であるべき値"),
    ("price", True),
])
def test_invalid_property_shapes_rejected_before_confirmation(reviewed_system, key, value):
    store, documents, _, _, _ = reviewed_system
    record = parsed(documents, "物件概要_demo.pdf")
    raw_before = json.dumps(record["raw"], ensure_ascii=False, sort_keys=True)
    review = copy.deepcopy(record["normalized"])
    review["property"][key] = value
    with pytest.raises(AppError) as rejected:
        documents.confirm(record["id"], review, "Isolated malformed review data", usage='customer')
    assert rejected.value.code == "INVALID_PROPERTY_VALUE"
    after = store.get("documents", record["id"])
    assert after["status"] == "parsed"
    assert json.dumps(after["raw"], ensure_ascii=False, sort_keys=True) == raw_before
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM confirmations").fetchone()[0] == 0
