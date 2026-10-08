"""Independent regression checks for pinned facts and explicit revocation.

Actual installed SDK parsing via HTTP, isolated SQLite, no paid AI/TTS.
"""
import copy
import uuid

from app.main import app
from app.services.knowledge_access import available_snapshot
from test_api import ADMIN, client, confirm_publish, upload_parse
from test_admin_drafts import get_draft, save, confirm


def test_rate_revision_confirmation_keeps_old_product_facts_and_calculation(client):
    _, parsed = upload_parse(client, name='住宅ローン_demo.xlsx')
    reviewed_source = copy.deepcopy(parsed['normalized'])
    rate_source = reviewed_source['rates'][0]
    reviewed_source['document'] = {
        'scope': 'general', 'source_name': 'TEST住宅ローン資料',
        'source_url': rate_source['source_url'], 'checked_at': rate_source['effective_date'],
        'effective_date': rate_source['effective_date'], 'valid_until': rate_source['valid_until'],
    }
    first = confirm_publish(client, parsed, reviewed_source)
    record_before = copy.deepcopy(app.state.store.get('documents', parsed['id']))
    session = client.post('/api/sessions', json={'mode': 'text'}).json()
    headers = {'X-Session-Token': session['token']}
    product = session['products'][0]
    amount = {'loan_amount': 30000000, 'years': 35, 'rate_id': product['id']}
    original = client.post(f"/api/sessions/{session['id']}/mortgage", json=amount, headers=headers)
    assert original.status_code == 200, original.text
    draft = get_draft(client, parsed['id'])
    reviewed = copy.deepcopy(draft['reviewed'])
    reviewed['rates'][0]['rate'] = 1.7  # TEST amendment; never a real bank fact.
    reviewed['rates'][0]['conditions'] = ['TEST新修訂の条件。旧版には混ぜない。']
    reviewed['rates'][0]['notes'] = 'TEST新修訂。実際の金利資料として使用しない。'
    saved = save(client, parsed['id'], draft, reviewed).json()
    response = confirm(client, parsed['id'], saved)
    assert response.status_code == 200, response.text
    assert app.state.store.latest()['version'] == first['version']
    for current in [session, client.post('/api/sessions', json={'mode': 'text'}).json()]:
        current_headers = {'X-Session-Token': current['token']}
        view = client.get(f"/api/sessions/{current['id']}", headers=current_headers)
        assert view.status_code == 200, view.text
        assert view.json()['version'] == first['version']
        assert view.json()['products'][0]['rate'] == product['rate']
        assert 'TEST新修訂' not in view.text
        calculation = client.post(f"/api/sessions/{current['id']}/mortgage", json=amount, headers=current_headers)
        assert calculation.status_code == 200, calculation.text
        assert calculation.json()['monthly_payment'] == original.json()['monthly_payment']
        assert calculation.json()['annual_interest_rate'] == original.json()['annual_interest_rate']
        assert calculation.json()['conditions'] == original.json()['conditions']
    record_after = app.state.store.get('documents', parsed['id'])
    assert record_after['raw'] == record_before['raw']
    assert record_after['normalized'] == record_before['normalized']
    assert available_snapshot(app.state.store, app.state.store.version(first['version']))['rates'][0]['rate'] == product['rate']


def test_explicit_revoke_then_reconfirm_cannot_reactivate_old_confirmation(client):
    _, parsed = upload_parse(client)
    first = confirm_publish(client, parsed)
    published = copy.deepcopy(app.state.store.version(first['version']))
    session = client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()
    headers = {'X-Session-Token': session['token']}
    for usage in ['internal', 'customer']:
        changed = client.post(f"/api/admin/documents/{parsed['id']}/usage", auth=ADMIN,
                              json={'usage': usage, 'note': 'TEST明示用途変更。履歴の許可を再利用しない。'})
        assert changed.status_code == 200, changed.text
    record = app.state.store.get('documents', parsed['id'])
    renewed = client.post(f"/api/admin/documents/{parsed['id']}/confirm", auth=ADMIN,
                          json={'usage': 'customer', 'reviewed': record['reviewed'], 'note': 'TEST改めて原資料を確認。新承認のみ。'})
    assert renewed.status_code == 200, renewed.text
    assert renewed.json()['confirmation_id'] != published['document_approvals'][parsed['id']]
    assert app.state.store.version(first['version']) == published
    assert available_snapshot(app.state.store, published)['property'] == {}
    refused = client.get(f"/api/sessions/{session['id']}", headers=headers)
    assert refused.status_code == 409
    assert refused.json()['error']['code'] == 'SESSION_RESTART_REQUIRED'


def test_failure_at_publication_receipt_rolls_back_version_and_is_retryable(client):
    _, parsed = upload_parse(client)
    first = confirm_publish(client, parsed)
    before_versions = copy.deepcopy(app.state.store.versions())
    before_record = copy.deepcopy(app.state.store.get('documents', parsed['id']))
    created = client.post('/api/admin/publication-drafts', json={}, auth=ADMIN)
    assert created.status_code == 200, created.text
    draft = created.json()
    saved = client.post(f"/api/admin/publication-drafts/{draft['id']}", auth=ADMIN,
                        json={'revision': draft['revision'], 'items': [
                            {'document_id': item['document_id'], 'confirmation_id': item['confirmation_id']}
                            for item in draft['items']], 'note': 'TEST公開確定の終盤でDB失敗を注入。原版を保持。'})
    assert saved.status_code == 200, saved.text
    preview = client.post(f"/api/admin/publication-drafts/{draft['id']}/preview", auth=ADMIN)
    assert preview.status_code == 200 and preview.json()['blockers'] == []
    body = {'draft_id': draft['id'], 'draft_revision': saved.json()['revision'],
            'preview_token': preview.json()['preview_token'], 'idempotency_key': uuid.uuid4().hex}
    # Failure is after the version INSERT and document/draft updates. The entire
    # transaction must roll back, including the receipt used for safe retries.
    with app.state.store.connect() as db:
        db.execute("CREATE TRIGGER TEST_fail_receipt BEFORE INSERT ON publication_submissions "
                   "BEGIN SELECT RAISE(ABORT, 'TEST injected receipt failure'); END")
    refused = client.post('/api/admin/publish', json=body, auth=ADMIN)
    assert refused.status_code == 500, refused.text
    assert app.state.store.versions() == before_versions
    assert app.state.store.get('documents', parsed['id']) == before_record
    state = client.get(f"/api/admin/publication-drafts/{draft['id']}", auth=ADMIN).json()
    assert state['state'] == 'open'
    assert client.post('/api/sessions', json={'mode': 'text'}).json()['version'] == first['version']
    with app.state.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM publication_submissions WHERE idempotency_key=?',
                          (body['idempotency_key'],)).fetchone()[0] == 0
        db.execute('DROP TRIGGER TEST_fail_receipt')
    succeeded = client.post('/api/admin/publish', json=body, auth=ADMIN)
    assert succeeded.status_code == 200, succeeded.text
    repeated = client.post('/api/admin/publish', json=body, auth=ADMIN)
    assert repeated.status_code == 200 and repeated.json()['replayed'] is True
    assert repeated.json()['version'] == succeeded.json()['version']
    assert len(app.state.store.versions()) == len(before_versions) + 1
