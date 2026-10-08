"""Isolated HTTP evidence helpers. Real SDK; no normal DB or paid providers.

Run --seed once after starting the dedicated 8003 test server. Business UI
acceptance is performed in real Google Chrome with cua_repl, not this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/phase2_document_update"
ORIGIN = "http://127.0.0.1:8003/api"
NAMES = ["物件概要_demo.pdf", "設備仕様_demo.pdf", "周辺環境_demo.pdf", "住宅購入基礎FAQ_demo.pdf", "住宅ローン基礎FAQ_demo.pdf", "住宅ローン_demo.xlsx"]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def safe(value):
    if isinstance(value, dict):
        return {key: safe(item) for key, item in value.items() if key not in {"token", "session_token", "api_key", "password", "authorization"}}
    if isinstance(value, list):
        return [safe(item) for item in value]
    return value


def dump(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(safe(value), ensure_ascii=False, indent=2), encoding="utf-8")


def client():
    return httpx.Client(base_url=ORIGIN, auth=("admin", "TEST-phase2-update-admin"), timeout=30, trust_env=False)


def checked(response):
    if response.status_code >= 400:
        raise RuntimeError(f"STOP {response.request.method} {response.request.url.path}: HTTP {response.status_code} {response.json().get('error', {}).get('code', 'UNKNOWN')}; no retry")
    return response.json()


def seed():
    records = {}
    with client() as http:
        known = checked(http.get("/admin/documents"))
        for name in NAMES:
            path = ROOT / "demo_documents" / name
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            match = next((row for row in known if row["sha256"] == file_hash), None)
            if match:
                record = checked(http.get(f"/admin/documents/{match['id']}"))
                if record["status"] == "error":
                    raise RuntimeError(f"STOP prior actual SDK error for {name}; no retry")
            else:
                with path.open("rb") as upload:
                    record = checked(http.post("/admin/documents", files={"file": (name, upload, "application/pdf" if name.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}))
                known.append(record)
            if record["status"] == "uploaded":
                record = checked(http.post(f"/admin/documents/{record['id']}/parse"))
            assert record["sdk_version"] == "1.8.0"
            assert record.get("raw") and record.get("normalized")
            before = {"raw_sha256": digest(record["raw"]), "normalized_sha256": digest(record["normalized"])}
            if not record.get("confirmation_id"):
                draft = checked(http.get(f"/admin/documents/{record['id']}/draft"))
                saved = checked(http.post(f"/admin/documents/{record['id']}/draft", json={
                    "document_sha256": draft["document_sha256"], "source_revision": draft["source_revision"], "revision": draft["revision"],
                    "reviewed": draft["reviewed"], "usage": "customer", "note": "TEST隔離資料。SDK実結果と原資料の照合。通常DB・実接客とは無関係。",
                }))
                record = checked(http.post(f"/admin/documents/{record['id']}/draft/confirm", json={
                    "document_sha256": saved["document_sha256"], "source_revision": saved["source_revision"], "revision": saved["revision"],
                    "note": "TEST隔離：原資料の内容・用途・出典・期限を明示確認。自動対客公開はしていない。",
                }))
            assert digest(record["raw"]) == before["raw_sha256"]
            assert digest(record["normalized"]) == before["normalized_sha256"]
            records[name] = {
                "id": record["id"], "filename": name, "sha256": record["sha256"], "sdk_version": record["sdk_version"], "sdk_api": record["sdk_api"],
                "parsed_at": record["parsed_at"], "confirmation_id": record["confirmation_id"], **before,
            }
            dump("sdk_parse_records.json", records)
        generate_test_replacement(http, records["物件概要_demo.pdf"]["id"])
    print(json.dumps({"seed_documents": len(records), "sdk": "REAL_INSTALLED_1.8.0", "normal_db": "NEVER_OPENED", "paid_calls": 0}, ensure_ascii=False))


def generate_test_replacement(http, original_id):
    """Test-owned native-text PDF, distinct hash; original identity retained."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_documents import business_pdf
    original = checked(http.get(f"/admin/documents/{original_id}"))
    prop = original["normalized"]["property"]
    replacement = OUT / "TEST_overview_replacement.pdf"
    if replacement.exists():
        return
    fields = ["property_name", "lot", "price", "address", "layout", "land_area", "building_area", "station", "walking_minutes", "completion_date", "parking", "scope_notes", "source_name", "source_url", "checked_at", "effective_date", "valid_until"]
    rows = [(key, 77900000 if key == "price" else prop.get(key)) for key in fields if prop.get(key) is not None]
    business_pdf(replacement, "TEST 物件概要差し替え", "TEST隔離専用。人工修正価格を含み、実際の販売資料ではありません。", rows,
                 ["TEST: 価格77,900,000円は更新・公開の操作検証専用の人工値です。通常環境や顧客資料には使用しません。"])
    dump("replacement_fixture.json", {"file": replacement.name, "source_document_id": original_id, "test_price": 77900000, "sha256": hashlib.sha256(replacement.read_bytes()).hexdigest(), "purpose": "TEST native text PDF actual SDK parsing; not real public fact"})


def publish_v1():
    """Explicit isolated initial release setup, not a Chrome operation."""
    with client() as http:
        versions = checked(http.get('/admin/versions'))
        if versions:
            raise RuntimeError('STOP v1 setup requires no existing published versions; no overwrite/retry')
        records = checked(http.get('/admin/documents'))
        rate_id = next(row['id'] for row in records if row['filename'] == '住宅ローン_demo.xlsx')
        source = checked(http.get(f'/admin/documents/{rate_id}'))
        # Installed adapter returns product dates, but does not claim these
        # document-level metadata. This is explicitly recorded TEST manual work.
        if not source['reviewed'].get('document', {}).get('valid_until'):
            draft = checked(http.get(f'/admin/documents/{rate_id}/draft'))
            product = draft['reviewed']['rates'][0]
            draft['reviewed']['document'].update(
                scope='general', source_name='TEST：住宅ローン資料（商品記載期間を資料単位に手動整理）',
                source_url=product['reference']['source_url'], checked_at=product.get('checked_at','2026-10-07'),
                effective_date=product['effective_date'], valid_until=product['valid_until'],
                scope_notes='TEST人工整理。資料単位の期間は掲載商品の期間を照合して設定。SDK認識結果の追記ではない。',
            )
            note='TEST人工整理：Excelの商品日付を原資料と照合し、共通知識範囲・資料単位の基準日と有効期限を設定。SDK raw/normalizedは未変更。'
            draft = checked(http.post(f'/admin/documents/{rate_id}/draft',json={
                'document_sha256':draft['document_sha256'],'source_revision':draft['source_revision'],'revision':draft['revision'],
                'reviewed':draft['reviewed'],'usage':'customer','note':note,
            }))
            checked(http.post(f'/admin/documents/{rate_id}/draft/confirm',json={
                'document_sha256':draft['document_sha256'],'source_revision':draft['source_revision'],'revision':draft['revision'],'note':note,
            }))
            dump('loan_metadata_manual_test.json',{'document_id':rate_id,'sdk_claim':False,'manual_test_metadata':draft['reviewed']['document'],'reason':note})
        rows = [checked(http.get(f"/admin/documents/{row['id']}")) for row in records]
        draft = checked(http.post('/admin/publication-drafts',json={}))
        draft = checked(http.post(f"/admin/publication-drafts/{draft['id']}",json={
            'revision':draft['revision'],'items':[{'document_id':row['id'],'confirmation_id':row['confirmation_id']} for row in rows],
            'note':'TEST v1初期公開：6資料を実SDK解析・明示確認。loan metadata/conditionsはTEST人工整理。Chrome操作ではなく隔離HTTP setup。',
        }))
        preview = checked(http.post(f"/admin/publication-drafts/{draft['id']}/preview"))
        dump('v1_setup_preview.json',preview)
        if preview['blockers']:
            raise RuntimeError('STOP v1 preview blockers: '+json.dumps(preview['blockers'],ensure_ascii=False))
        version = checked(http.post('/admin/publish',json={
            'draft_id':draft['id'],'draft_revision':preview['draft_revision'],'preview_token':preview['preview_token'],'idempotency_key':str(uuid.uuid4()),
        }))
        assert version['version']==1 and len(version['document_ids'])==6
        dump('v1_setup.json',{'method':'REAL_ISOLATED_HTTP_SETUP_NOT_CHROME','version':version,'preview':preview,'paid_calls':0})
        print('TEST v1 initial six-document preview-gated publication: PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--publish-v1", action="store_true")
    args = parser.parse_args()
    if args.seed:
        seed()
    elif args.publish_v1:
        publish_v1()
    else:
        parser.error("Specify --seed; browser acceptance uses cua_repl separately")


if __name__ == "__main__":
    main()
