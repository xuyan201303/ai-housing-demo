"""Isolated HTTP tests with the real installed SANZO SDK; no external AI calls."""
import asyncio
import copy
import importlib
import json
import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.repositories.store import Store
from app.services.ai import AiService
from app.services.documents import DocumentService
from app.services.sessions import SessionService
from app.services.tools import ToolService

ROOT = Path(__file__).resolve().parents[2]
ADMIN = ('admin', 'TEST-admin-password')
STAFF = ('staff', 'TEST-staff-password')


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Never initialize or mutate the application's demo data/uploads directories.
    monkeypatch.setattr(settings, 'database', tmp_path / 'http-tests.db')
    monkeypatch.setattr(settings, 'upload_dir', tmp_path / 'uploads')
    monkeypatch.setattr(settings, 'admin_password', ADMIN[1])
    monkeypatch.setattr(settings, 'staff_password', STAFF[1])
    monkeypatch.setattr(settings, 'api_key', '')
    for module in ['app.models.domain', 'app.services.documents', 'app.services.sessions', 'app.services.tools', 'app.services.staff', 'app.services.ai']:
        monkeypatch.setattr(importlib.import_module(module), 'now', lambda: '2026-10-07T12:00:00+09:00')
    store = Store(settings.database)
    documents = DocumentService(store, settings)
    tools = ToolService(store)
    monkeypatch.setattr(app.state, 'store', store)
    monkeypatch.setattr(app.state, 'documents', documents)
    monkeypatch.setattr(app.state, 'sessions', SessionService(store))
    monkeypatch.setattr(app.state, 'tools', tools)
    monkeypatch.setattr(app.state, 'ai', AiService(store, tools, settings))
    monkeypatch.setattr(app.state, 'parse_lock', asyncio.Lock())
    with TestClient(app, raise_server_exceptions=False) as value:
        yield value


def upload_parse(client, name='物件概要_demo.pdf', upload_name=None):
    file = ROOT / 'demo_documents' / name
    content_type = 'application/pdf' if file.suffix == '.pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response = client.post('/api/admin/documents', data={'duplicate_action': 'separate'}, files={'file': (upload_name or file.name, file.read_bytes(), content_type)}, auth=ADMIN)
    assert response.status_code == 200, response.text
    uploaded = response.json()
    assert uploaded['status'] == 'uploaded'
    parsed = client.post(f"/api/admin/documents/{uploaded['id']}/parse", auth=ADMIN)
    assert parsed.status_code == 200, parsed.text
    return uploaded, parsed.json()


def amend_test_price(review, amount):
    """Explicit TEST employee edits both business value and reviewed body.

    This is test input preparation, never production auto-rewriting or SDK fact.
    The immutable raw and normalized source continue to carry their old values.
    """
    review['property']['price'] = amount
    for item in review.get('knowledge', []):
        item['text'] = re.sub(r'(?m)^(\s*price\s*:\s*)[0-9]+(?:\.[0-9]+)?\s*$', lambda m: m.group(1) + str(amount), item.get('text', ''))
    return review


def publish_documents(client, document_ids, note='TEST公開内容を社員が確認', auth=ADMIN):
    """All HTTP regressions exercise the preview-gated contract, including rejection."""
    draft = client.post('/api/admin/publication-drafts', json={}, auth=auth).json()
    items = [{'document_id': id, 'confirmation_id': client.get(f'/api/admin/documents/{id}', auth=auth).json().get('confirmation_id')} for id in document_ids]
    saved = client.post(f"/api/admin/publication-drafts/{draft['id']}", json={'revision': draft['revision'], 'items': items, 'note': note}, auth=auth)
    assert saved.status_code == 200, saved.text
    draft = saved.json()
    preview = client.post(f"/api/admin/publication-drafts/{draft['id']}/preview", auth=auth)
    assert preview.status_code == 200, preview.text
    return client.post('/api/admin/publish', json={'draft_id': draft['id'], 'draft_revision': draft['revision'],
                      'preview_token': preview.json()['preview_token'], 'idempotency_key': uuid.uuid4().hex}, auth=auth)


def confirm_publish(client, parsed, review=None):
    review = copy.deepcopy(review or parsed['normalized'])
    result = client.post(f"/api/admin/documents/{parsed['id']}/confirm", json={'usage':'customer', 'reviewed': review, 'note': 'TEST隔離HTTP確認'}, auth=ADMIN)
    assert result.status_code == 200, result.text
    published = publish_documents(client, [parsed['id']])
    assert published.status_code == 200, published.text
    return published.json()


def start(client):
    response = client.post('/api/sessions', json={'mode': 'text', 'property_id':'No.15'})
    assert response.status_code == 200, response.text
    session = response.json()
    return session, {'X-Session-Token': session['token']}


def test_real_sdk_http_lifecycle_and_versions(client):
    uploaded, parsed = upload_parse(client)
    assert parsed['sdk_api'] == 'document_sdk.pdf.extract_native_text'
    assert parsed['sdk_version'] == '1.8.0'
    assert parsed['raw']['pages']
    assert parsed['normalized']['property']['price'] == 76900000
    unpublished = publish_documents(client, [uploaded['id']])
    assert unpublished.status_code == 409
    assert unpublished.json()['error']['code'] == 'UNCONFIRMED_DOCUMENT'
    v1 = confirm_publish(client, parsed)
    s1, headers1 = start(client)
    _, updated = upload_parse(client)
    amended = copy.deepcopy(updated['normalized'])
    amend_test_price(amended, 77000000)  # TEST employee edits reviewed fields and body consistently.
    v2 = confirm_publish(client, updated, amended)
    s2, headers2 = start(client)
    assert v2['version'] > v1['version']
    assert s1['version'] == v1['version']
    assert s2['version'] == v2['version']
    old = client.get(f"/api/sessions/{s1['id']}", headers=headers1).json()
    new = client.get(f"/api/sessions/{s2['id']}", headers=headers2).json()
    assert old['property']['price'] == 76900000
    assert new['property']['price'] == 77000000
    assert 'token' not in old
    source = old['property']['references'][0]
    assert source['label'] == '確認・公開済み物件資料'
    assert 'filename' not in source and 'document_id' not in source
    # Source identity remains in authorized audit data, not the Customer wire.
    audit = client.get('/api/admin/sessions', auth=ADMIN).json()
    original = next(s for s in audit if s['id'] == s1['id'])
    assert original['snapshot']['references'][0]['document_id'] == parsed['id']
    document = client.get(f"/api/admin/documents/{parsed['id']}", auth=ADMIN).json()
    assert document['raw'] == parsed['raw']
    assert document['status'] == 'published'


def test_excel_http_calls_installed_sdk(client):
    _, parsed = upload_parse(client, '住宅ローン_demo.xlsx')
    assert parsed['sdk_api'] == 'document_sdk.excel.inspect_workbook + read_sheet'
    assert parsed['raw']['sheets']
    rates = parsed['normalized']['rates']
    assert rates[1]['rate'] == 3.83
    assert rates[1]['rate_over_90_percent'] == 3.94
    assert parsed['normalized']['knowledge'] == []


def test_admin_and_staff_auth_boundaries(client):
    assert client.get('/api/admin/documents').status_code == 401
    assert client.get('/api/admin/documents', auth=('admin', 'wrong')).status_code == 401
    assert client.get('/api/admin/documents', auth=STAFF).status_code == 401
    assert client.get('/api/admin/documents', auth=ADMIN).status_code == 200
    assert client.get('/api/staff/calls').status_code == 401
    assert client.get('/api/staff/calls', auth=STAFF).status_code == 200
    assert client.get('/api/staff/calls', auth=ADMIN).status_code == 200


def test_filename_cannot_choose_storage_path(client):
    uploaded, parsed = upload_parse(client, upload_name='../../escape/物件概要_demo.pdf')
    assert uploaded['filename'] == '物件概要_demo.pdf'
    stored = list(settings.upload_dir.iterdir())
    assert len(stored) == 1
    assert stored[0].name == uploaded['id'] + '.pdf'
    assert not (settings.upload_dir.parent / 'escape').exists()
    assert str(settings.upload_dir) not in json.dumps(parsed, ensure_ascii=False)


@pytest.mark.parametrize('filename,body,expected', [('x.exe', b'test', 'UNSUPPORTED_FILE'), ('x.pdf', b'not a PDF', 'FILE_SIGNATURE'), ('x.xlsx', b'not a ZIP', 'FILE_SIGNATURE')])
def test_upload_type_and_magic_are_checked(client, filename, body, expected):
    response = client.post('/api/admin/documents', files={'file': (filename, body)}, auth=ADMIN)
    assert response.status_code == 415
    assert response.json()['error']['code'] == expected
    assert client.get('/api/admin/documents', auth=ADMIN).json() == []


def test_upload_resource_limit(client, monkeypatch):
    monkeypatch.setattr(settings, 'max_upload_bytes', 128)
    response = client.post('/api/admin/documents', files={'file': ('large.pdf', b'%PDF-' + b'x' * 200)}, auth=ADMIN)
    assert response.status_code == 413
    assert response.json()['error']['code'] == 'UPLOAD_SIZE'
    assert client.get('/api/admin/documents', auth=ADMIN).json() == []
    response = client.post('/api/admin/documents', content=b'x', headers={'Content-Length': '100000'}, auth=ADMIN)
    assert response.status_code == 413
    assert response.json()['error']['code'] == 'REQUEST_SIZE'


def test_chunked_body_cannot_bypass_request_limit(client, monkeypatch):
    monkeypatch.setattr(settings, 'max_upload_bytes', 128)
    boundary = 'TEST-multipart-boundary'
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="large.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
        + b'%PDF-' + b'x' * 70000 + f'\r\n--{boundary}--\r\n'.encode()
    )
    response = client.post('/api/admin/documents', content=(body[index:index + 1024] for index in range(0, len(body), 1024)), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}, auth=ADMIN)
    assert response.status_code == 413, response.text
    assert response.json()['error']['code'] == 'REQUEST_SIZE'
    assert client.get('/api/admin/documents', auth=ADMIN).json() == []


def test_sdk_failure_is_real_error_and_sanitized(client):
    uploaded = client.post('/api/admin/documents', files={'file': ('broken.pdf', b'%PDF-1.7\nBroken TEST input')}, auth=ADMIN).json()
    response = client.post(f"/api/admin/documents/{uploaded['id']}/parse", auth=ADMIN)
    assert response.status_code == 422, response.text
    payload = response.json()
    assert payload['error']['code'].startswith('SDK_')
    assert str(settings.upload_dir) not in response.text
    stored = client.get(f"/api/admin/documents/{uploaded['id']}", auth=ADMIN).json()
    assert stored['status'] == 'error'
    assert 'raw' not in stored
    assert stored['error']['code'] == payload['error']['code']


def test_internal_exception_does_not_expose_path_or_secret(client, monkeypatch):
    _, parsed = upload_parse(client)

    def fail(id):
        raise RuntimeError('/Users/private/path SECRET_TEST_CREDENTIAL')

    monkeypatch.setattr(app.state.documents, 'parse', fail)
    response = client.post(f"/api/admin/documents/{parsed['id']}/parse", auth=ADMIN)
    assert response.status_code == 500
    assert response.json()['error']['code'] == 'INTERNAL_ERROR'
    assert '/Users/private' not in response.text
    assert 'SECRET_TEST_CREDENTIAL' not in response.text


def test_session_auth_end_and_missing_ai_key_are_explicit(client):
    _, parsed = upload_parse(client)
    confirm_publish(client, parsed)
    session, headers = start(client)
    path = f"/api/sessions/{session['id']}"
    assert client.get(path).status_code == 403
    assert client.get(path, headers={'X-Session-Token': 'wrong'}).status_code == 403
    missing_key = client.post(path + '/messages', headers=headers, json={'text': 'この家の設備を教えてください'})
    assert missing_key.status_code == 503
    assert missing_key.json()['error']['code'] == 'OPENAI_NOT_CONFIGURED'
    messages = client.get(path, headers=headers).json()['messages']
    assert len(messages) == 1 and messages[0]['role'] == 'user'
    ended = client.post(path + '/end', headers=headers)
    assert ended.status_code == 200
    assert ended.json()['status'] == 'ended'
    assert client.post(path + '/messages', headers=headers, json={'text': 'こんにちは'}).status_code == 409
    assert client.post(path + '/staff-calls', headers=headers, json={'reason': '相談'}).status_code == 409
    assert client.get(path, headers=headers).status_code == 200


def test_end_preserves_realtime_close_written_after_session_authorization(client, monkeypatch):
    _, parsed = upload_parse(client)
    confirm_publish(client, parsed)
    session, headers = start(client)
    value = app.state.store.get('sessions', session['id'])
    value['realtime'] = {'status': 'connected'}
    app.state.store.put('sessions', value)

    async def scripted_close(id):
        latest = app.state.store.get('sessions', id)
        latest['realtime'] = {'status': 'closed', 'upstream_hangup_status': 200}
        app.state.store.put('sessions', latest)

    monkeypatch.setattr(app.state.realtime, 'close', scripted_close)
    path = f"/api/sessions/{session['id']}"
    response = client.post(path + '/end', headers=headers)
    assert response.status_code == 200
    assert response.json()['status'] == 'ended'
    assert response.json()['realtime'] == {'status': 'closed', 'error': None}
    assert 'token' not in response.json()
    assert app.state.store.get('sessions', session['id'])['realtime']['upstream_hangup_status'] == 200
    assert client.get(path, headers=headers).json()['realtime']['status'] == 'closed'


def test_expired_property_cannot_be_published(client):
    _, parsed = upload_parse(client)
    review = copy.deepcopy(parsed['normalized'])
    review['property']['valid_until'] = '2000-01-01'
    assert client.post(f"/api/admin/documents/{parsed['id']}/confirm", json={'usage':'customer', 'reviewed': review, 'note': 'TEST expired date'}, auth=ADMIN).status_code == 200
    response = publish_documents(client, [parsed['id']])
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'DOCUMENT_EXPIRED'


def test_expired_published_property_prevents_new_session(client, monkeypatch):
    _, parsed = upload_parse(client)
    confirm_publish(client, parsed)
    monkeypatch.setattr(importlib.import_module('app.services.sessions'), 'now', lambda: '2026-10-16T12:00:00+09:00')
    response = client.post('/api/sessions', json={'mode': 'text', 'property_id':'No.15'})
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'PROPERTY_EXPIRED'


def test_future_property_cannot_be_published(client):
    _, parsed = upload_parse(client)
    review = copy.deepcopy(parsed['normalized'])
    review['property'].update(effective_date='2099-01-01', valid_until='2099-12-31')
    assert client.post(f"/api/admin/documents/{parsed['id']}/confirm", json={'usage':'customer', 'reviewed': review, 'note': 'TEST future date'}, auth=ADMIN).status_code == 200
    response = publish_documents(client, [parsed['id']])
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'DOCUMENT_NOT_YET_EFFECTIVE'


def test_future_published_property_prevents_new_session(client, monkeypatch):
    _, parsed = upload_parse(client)
    confirm_publish(client, parsed)
    monkeypatch.setattr(importlib.import_module('app.services.sessions'), 'now', lambda: '2026-10-01T12:00:00+09:00')
    response = client.post('/api/sessions', json={'mode': 'text', 'property_id':'No.15'})
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'PROPERTY_NOT_YET_EFFECTIVE'
