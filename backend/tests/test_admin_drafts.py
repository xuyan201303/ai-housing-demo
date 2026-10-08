"""Admin form drafts over the actual APIs, installed SDK, and isolated SQLite."""
import copy
import json

import pytest

from test_api import ADMIN, STAFF, client, confirm_publish, publish_documents, amend_test_price, upload_parse
from app.main import app
from app.services.knowledge_access import available_snapshot


def get_draft(client, document_id):
    response = client.get(f'/api/admin/documents/{document_id}/draft', auth=ADMIN)
    assert response.status_code == 200, response.text
    return response.json()


def save(client, document_id, envelope, reviewed=None, usage='customer', note='TEST社員フォーム編集'):
    body = {key: envelope[key] for key in ('document_sha256', 'source_revision', 'revision')}
    body.update(reviewed=copy.deepcopy(reviewed if reviewed is not None else envelope['reviewed']), usage=usage, note=note)
    return client.post(f'/api/admin/documents/{document_id}/draft', json=body, auth=ADMIN)


def confirm(client, document_id, envelope, note='TEST社員が内容と用途を確認'):
    body = {key: envelope[key] for key in ('document_sha256', 'source_revision', 'revision')}
    body['note'] = note
    return client.post(f'/api/admin/documents/{document_id}/draft/confirm', json=body, auth=ADMIN)


def fingerprint(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def test_real_sdk_draft_persistence_and_candidate_fields_do_not_become_facts(client):
    _, parsed = upload_parse(client)
    id = parsed['id']
    before = fingerprint(parsed['raw']), fingerprint(parsed['normalized'])
    candidate = get_draft(client, id)
    assert candidate['revision'] == 0 and candidate['usage'] == 'unclassified'
    assert candidate['reviewed'] == parsed['normalized']
    edited = copy.deepcopy(candidate['reviewed'])
    edited['property'].update(property_name='TEST手動候補住宅', price=77000000,
                               equipment=['TEST設備を追加', 'TEST設備を修正'])
    edited['faq'] = [{'question': 'TEST駐車場はありますか？', 'answer': 'TEST原本を確認してください。',
                     'source_url': 'https://example.invalid/TEST-public', 'reference': {'location': 'TEST p.1', 'extra_locator': 'TEST保留項目'}}]
    edited['document'] = {'scope': 'property', 'unsupported_existing_metadata': 'TEST保存を維持'}
    response = save(client, id, candidate, edited)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved['revision'] == 1 and saved['saved_by'] == 'admin'
    assert saved['confirmed_at'] is None
    # GET from the server after a fresh request reconstructs the persisted draft.
    restored = get_draft(client, id)
    assert restored['reviewed'] == edited and restored['note'] == 'TEST社員フォーム編集'
    record = app.state.store.get('documents', id)
    assert (fingerprint(record['raw']), fingerprint(record['normalized'])) == before
    assert record['status'] == 'parsed' and record['usage'] == 'unclassified'
    assert 'reviewed' not in record and not record.get('confirmed_at')
    with app.state.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM confirmations').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM versions').fetchone()[0] == 0
    listing = client.get('/api/admin/documents', auth=ADMIN).json()[0]
    assert listing['has_draft'] and listing['draft_revision'] == 1
    assert 'draft' not in listing and 'TEST手動候補住宅' not in fingerprint(listing)
    assert publish_documents(client, [id]).status_code == 409
    empty_session = client.post('/api/sessions', json={'mode': 'text'})
    assert empty_session.status_code == 200
    assert empty_session.json()['version'] is None and empty_session.json()['property'] is None
    assert 'TEST手動候補住宅' not in empty_session.text
    # Unknown top-level review keys are explicit errors, never silently removed.
    rejected = copy.deepcopy(edited)
    rejected['unsupported_top_level'] = 'TEST未知'
    response = save(client, id, restored, rejected)
    assert response.status_code == 422
    assert response.json()['error']['field_errors']['unsupported_top_level'] == '対応していない項目です。'
    assert get_draft(client, id)['revision'] == 1


def test_published_draft_save_preserves_current_customer_and_old_version_until_explicit_confirmation(client):
    _, parsed = upload_parse(client)
    version = confirm_publish(client, parsed)
    id = parsed['id']
    original = copy.deepcopy(app.state.store.get('documents', id))
    original_snapshot = fingerprint(app.state.store.version(version['version']))
    session = client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()
    headers = {'X-Session-Token': session['token']}
    draft = get_draft(client, id)
    edited = copy.deepcopy(draft['reviewed'])
    amend_test_price(edited, 78000000)  # Explicit TEST reviewed-body edit; original SDK evidence unchanged.
    edited['faq'] = [{'question': 'TEST追加の質問', 'answer': 'TEST下書きにだけある回答',
                      'reference': {'location': 'TEST社員確認', 'extra_locator': 'TEST未対応項目', 'document_id': 'wrong-file'}}]
    saved = save(client, id, draft, edited).json()
    unchanged = app.state.store.get('documents', id)
    for key in ('raw', 'normalized', 'reviewed', 'status', 'confirmed_at', 'confirmation_id', 'usage', 'published_version'):
        assert unchanged[key] == original[key]
    assert fingerprint(app.state.store.version(version['version'])) == original_snapshot
    assert available_snapshot(app.state.store, app.state.store.latest())['property']['price'] == 76900000
    customer = client.get(f"/api/sessions/{session['id']}", headers=headers)
    assert customer.status_code == 200 and customer.json()['property']['price'] == 76900000
    assert 'TEST下書きにだけある回答' not in customer.text and 'draft' not in customer.text
    confirmed = confirm(client, id, saved)
    assert confirmed.status_code == 200, confirmed.text
    rec = confirmed.json()
    assert rec['status'] == 'confirmed' and rec['reviewed']['property']['price'] == 78000000
    assert rec['confirmation_id'] != original['confirmation_id']
    assert rec['draft']['confirmed_at'] == rec['confirmed_at']
    reference = rec['reviewed']['faq'][0]['reference']
    assert reference['extra_locator'] == 'TEST未対応項目' and reference['document_id'] == id
    assert fingerprint(rec['raw']) == fingerprint(original['raw'])
    assert fingerprint(app.state.store.version(version['version'])) == original_snapshot
    # Ordinary revision confirmation keeps the immutable v1 approval; explicit revocation is tested separately.
    stale = client.get(f"/api/sessions/{session['id']}", headers=headers)
    assert stale.status_code == 200 and stale.json()['property']['price'] == 76900000
    assert available_snapshot(app.state.store, app.state.store.latest())['property']['price'] == 76900000
    again = confirm(client, id, get_draft(client, id))
    assert again.status_code == 409 and again.json()['error']['code'] == 'DRAFT_REQUIRED'
    new_version = publish_documents(client, [id])
    assert new_version.status_code == 200, new_version.text
    assert new_version.json()['version'] > version['version']
    assert new_version.json()['property']['price'] == 78000000
    assert fingerprint(app.state.store.version(version['version'])) == original_snapshot


def test_document_identity_draft_conflict_and_usage_change_source_revision(client):
    _, parsed = upload_parse(client)
    _, other = upload_parse(client, name='設備仕様_demo.pdf')
    id = parsed['id']
    candidate = get_draft(client, id)
    wrong = dict(candidate, document_sha256=other['sha256'])
    response = save(client, id, wrong)
    assert response.status_code == 409 and response.json()['error']['code'] == 'DRAFT_DOCUMENT_MISMATCH'
    first = save(client, id, candidate)
    assert first.status_code == 200
    response = save(client, id, candidate)
    assert response.status_code == 409 and response.json()['error']['code'] == 'DRAFT_CONFLICT'
    stale = first.json()
    change = client.post(f'/api/admin/documents/{id}/usage', json={'usage': 'internal', 'note': 'TEST社内用途確認'}, auth=ADMIN)
    assert change.status_code == 200
    fresh = get_draft(client, id)
    assert fresh['stale'] and fresh['source_revision'] != stale['source_revision']
    for response in (save(client, id, stale), confirm(client, id, stale)):
        assert response.status_code == 409 and response.json()['error']['code'] == 'DRAFT_SOURCE_CHANGED'
    assert app.state.store.get('documents', id)['usage'] == 'internal'


def test_incomplete_rate_draft_is_saved_with_no_approval_and_japanese_confirmation_errors(client):
    _, parsed = upload_parse(client, name='住宅ローン_demo.xlsx')
    id = parsed['id']
    candidate = get_draft(client, id)
    reviewed = copy.deepcopy(candidate['reviewed'])
    original_extra = reviewed['rates'][1]['rate_over_90_percent']
    reviewed['rates'][0]['valid_until'] = ''
    reviewed['rates'][0]['reference']['extra_locator'] = 'TEST保存する出典情報'
    response = save(client, id, candidate, reviewed)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved['reviewed']['rates'][1]['rate_over_90_percent'] == original_extra
    assert saved['reviewed']['rates'][0]['reference']['extra_locator'] == 'TEST保存する出典情報'
    response = confirm(client, id, saved)
    assert response.status_code == 400
    assert response.json()['error']['field_errors']['rates.0.valid_until'] == '金利の有効期限を入力してください。'
    assert app.state.store.get('documents', id)['status'] == 'parsed'
    with app.state.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM confirmations').fetchone()[0] == 0
    reviewed['rates'][0]['valid_until'] = '2026-01-01'
    rejected = save(client, id, saved, reviewed)
    assert rejected.status_code == 400
    assert rejected.json()['error']['field_errors']['rates.0.valid_until'] == '金利の有効期限は基準日以降の日付を入力してください。'


@pytest.mark.parametrize('usage', ['internal', 'unclassified'])
def test_draft_confirmation_does_not_grant_customer_usage_implicitly(client, usage):
    _, parsed = upload_parse(client)
    id = parsed['id']
    saved = save(client, id, get_draft(client, id), usage=usage).json()
    approved = confirm(client, id, saved)
    assert approved.status_code == 200 and approved.json()['usage'] == usage
    response = publish_documents(client, [id])
    assert response.status_code == 409 and response.json()['error']['code'] == 'CUSTOMER_USAGE_REQUIRED'


def test_admin_only_draft_access_and_field_type_errors(client):
    _, parsed = upload_parse(client)
    id = parsed['id']
    candidate = get_draft(client, id)
    body = {key: candidate[key] for key in ('document_sha256', 'source_revision', 'revision')}
    body.update(reviewed=candidate['reviewed'], usage='customer', note='TEST')
    confirm_body = {key: candidate[key] for key in ('document_sha256', 'source_revision')}
    confirm_body.update(revision=1, note='TEST')
    for auth in (None, STAFF, ('admin', 'wrong-TEST-password')):
        assert client.get(f'/api/admin/documents/{id}/draft', auth=auth).status_code == 401
        assert client.post(f'/api/admin/documents/{id}/draft', json=body, auth=auth).status_code == 401
        assert client.post(f'/api/admin/documents/{id}/draft/confirm', json=confirm_body, auth=auth).status_code == 401
    edited = copy.deepcopy(candidate['reviewed'])
    edited['property']['price'] = -1
    edited['faq'] = [{'question': 42, 'answer': ''}]
    response = save(client, id, candidate, edited)
    assert response.status_code == 400
    fields = response.json()['error']['field_errors']
    assert fields['property.price'] == '価格は0以上の数値で入力してください。'
    assert fields['faq.0.question'] == '質問を入力してください。'
    assert get_draft(client, id)['revision'] == 0


@pytest.mark.parametrize('key,value,expected_field', [
    ('years_min', '二十年', 'years_min'),
    ('years_min', -1, 'years_min'),
    ('years_min', 2.5, 'years_min'),
    ('years_max', 51, 'years_max'),
    ('years_min', 41, 'years_max'),
    ('loan_amount_min', '五百万円', 'loan_amount_min'),
    ('loan_amount_max', -1, 'loan_amount_max'),
    ('loan_amount_min', 300000001, 'loan_amount_max'),
    ('max_loan_to_value', 0, 'max_loan_to_value'),
    ('rate_over_90_percent', 21, 'rate_over_90_percent'),
    ('rate_over_90_percent', True, 'rate_over_90_percent'),
])
def test_editable_existing_borrowing_conditions_get_field_errors(client, key, value, expected_field):
    _, parsed = upload_parse(client, name='住宅ローン_demo.xlsx')
    candidate = get_draft(client, parsed['id'])
    reviewed = copy.deepcopy(candidate['reviewed'])
    reviewed['rates'][0][key] = value
    response = save(client, parsed['id'], candidate, reviewed)
    assert response.status_code == 400
    assert f'rates.0.{expected_field}' in response.json()['error']['field_errors']
    assert get_draft(client, parsed['id'])['revision'] == 0
