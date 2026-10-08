"""Actual Admin APIs and installed SDK; all mutations are isolated TEST scenarios."""
import copy
import hashlib
import json
import uuid

from app.main import app
from app.services.knowledge_access import available_snapshot
from test_api import ADMIN, STAFF, client, upload_parse, confirm_publish, publish_documents, amend_test_price
from test_admin_drafts import get_draft, save, confirm


def create(client, restore=None):
    r = client.post('/api/admin/publication-drafts', json={} if restore is None else {'restore_version': restore}, auth=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()


def edit(client, draft, items=None):
    body = {'revision': draft['revision'], 'items': items if items is not None else [{k: i[k] for k in ('document_id', 'confirmation_id')} for i in draft['items']], 'note': 'TEST社員が変更と公開範囲を確認'}
    r = client.post(f"/api/admin/publication-drafts/{draft['id']}", json=body, auth=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()


def preview(client, draft):
    r = client.post(f"/api/admin/publication-drafts/{draft['id']}/preview", auth=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()


def commit(client, draft, view, key=None):
    return client.post('/api/admin/publish', json={'draft_id': draft['id'], 'draft_revision': draft['revision'], 'preview_token': view['preview_token'], 'idempotency_key': key or uuid.uuid4().hex}, auth=ADMIN)


def approved(client, name):
    _, parsed = upload_parse(client, name=name)
    review = copy.deepcopy(parsed['normalized'])
    if name.endswith('.xlsx'):
        rate = review['rates'][0]
        review['document'] = {'scope': 'general', 'source_name': 'TEST社員整理：住宅ローン資料', 'source_url': rate['source_url'], 'checked_at': '2026-10-07', 'effective_date': rate['effective_date'], 'valid_until': rate['valid_until']}
    r = client.post(f"/api/admin/documents/{parsed['id']}/confirm", json={'reviewed': review, 'usage': 'customer', 'note': 'TEST実SDK抽出内容を社員確認'}, auth=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()


def test_real_sdk_collection_one_revision_preserves_other_sources_and_restore(client):
    names = ['物件概要_demo.pdf', '設備仕様_demo.pdf', '周辺環境_demo.pdf', '住宅購入基礎FAQ_demo.pdf', '住宅ローン基礎FAQ_demo.pdf', '住宅ローン_demo.xlsx']
    records = [approved(client, name) for name in names]
    v1r = publish_documents(client, [r['id'] for r in records]); assert v1r.status_code == 200, v1r.text
    v1 = v1r.json(); frozen_v1 = copy.deepcopy(app.state.store.version(v1['version']))
    old = client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()
    overview = records[0]; basis = get_draft(client, overview['id']); review = copy.deepcopy(basis['reviewed']); amend_test_price(review, 78000000)
    saved = save(client, overview['id'], basis, review).json(); new = confirm(client, overview['id'], saved).json()
    assert new['confirmation_id'] != v1['document_approvals'][overview['id']]
    assert app.state.store.version(v1['version']) == frozen_v1
    assert available_snapshot(app.state.store, app.state.store.latest())['property']['price'] == 76900000
    assert client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()['property']['price'] == 76900000
    draft = create(client); assert len(draft['items']) == len(records)
    assert next(i for i in draft['items'] if i['document_id'] == overview['id'])['confirmation_id'] == v1['document_approvals'][overview['id']]
    items = [{'document_id': i['document_id'], 'confirmation_id': new['confirmation_id'] if i['document_id'] == overview['id'] else i['confirmation_id']} for i in draft['items']]
    draft = edit(client, draft, items)
    restored_draft = client.get(f"/api/admin/publication-drafts/{draft['id']}", auth=ADMIN).json()
    assert restored_draft['note'] == draft['note'] and restored_draft['revision'] == draft['revision']
    view = preview(client, draft)
    assert len(view['replaced']) == 1 and len(view['retained']) == 5 and not view['added'] and not view['removed'] and not view['blockers']
    assert any(c['label'] == '価格' and c['before'] == 76900000 and c['after'] == 78000000 for c in view['changes'])
    key = uuid.uuid4().hex; result = commit(client, draft, view, key); assert result.status_code == 200, result.text
    v2 = result.json(); assert v2['property']['price'] == 78000000 and v2['document_approvals'] == {i['document_id']: i['confirmation_id'] for i in items}
    assert v2['rates'] == v1['rates'] and v2['faq'] == v1['faq'] and v2['property']['equipment'] == v1['property']['equipment']
    assert client.get(f"/api/sessions/{old['id']}", headers={'X-Session-Token': old['token']}).json()['property']['price'] == 76900000
    assert client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()['property']['price'] == 78000000
    replay = commit(client, draft, view, key); assert replay.status_code == 200 and replay.json()['version'] == v2['version'] and replay.json()['replayed']
    assert len(app.state.store.versions()) == 2
    restore = create(client, v1['version']); restore = edit(client, restore); restoration = preview(client, restore)
    assert len(restoration['replaced']) == 1 and not restoration['blockers']
    v3 = commit(client, restore, restoration).json(); assert v3['version'] > v2['version'] and v3['property']['price'] == 76900000
    assert app.state.store.version(v1['version']) == frozen_v1
    history = client.get('/api/admin/versions', auth=ADMIN).json()
    assert [v['version'] for v in history] == [v3['version'], v2['version'], v1['version']]
    assert all(v['published_by'] == 'admin' and v['actor_label'] == '共有管理者 (admin)' for v in history)
    assert client.post('/api/admin/publish', json={'document_ids': [overview['id']]}, auth=ADMIN).json()['error']['code'] == 'PUBLICATION_PREVIEW_REQUIRED'


def test_conditions_order_unknown_fields_persist_without_changing_notes_or_sdk_raw(client):
    record = approved(client, '住宅ローン_demo.xlsx'); raw = copy.deepcopy(record['raw']); normalized = copy.deepcopy(record['normalized'])
    d = get_draft(client, record['id']); review = copy.deepcopy(d['reviewed']); notes = review['rates'][0]['notes']
    review['rates'][0]['conditions'] = ['TEST第3条件を先頭に移動', 'TEST第1条件を修正', 'TEST第2条件を追加']
    review['rates'][0]['unknown_existing_extension'] = {'preserve': ['TEST値']}
    saved = save(client, record['id'], d, review).json()
    again = get_draft(client, record['id']); assert again['reviewed'] == review
    result = confirm(client, record['id'], saved); assert result.status_code == 200, result.text
    proof = result.json()['reviewed']['rates'][0]
    assert proof['conditions'] == review['rates'][0]['conditions'] and proof['notes'] == notes
    assert proof['unknown_existing_extension'] == {'preserve': ['TEST値']}
    assert result.json()['raw'] == raw and result.json()['normalized'] == normalized
    bad = get_draft(client, record['id']); invalid = copy.deepcopy(bad['reviewed']); invalid['rates'][0]['conditions'] = ['TEST', 42]
    failure = save(client, record['id'], bad, invalid)
    assert failure.status_code == 400 and 'rates.0.conditions' in failure.json()['error']['field_errors']


def test_stale_draft_parallel_publish_and_changed_approval_require_new_preview(client):
    _, parsed = upload_parse(client); v1 = confirm_publish(client, parsed)
    first = edit(client, create(client)); second = edit(client, create(client)); p1 = preview(client, first); p2 = preview(client, second)
    concurrent_edit = client.post(f"/api/admin/publication-drafts/{first['id']}", json={'revision': 0, 'items': [], 'note': 'TEST stale'}, auth=ADMIN)
    assert concurrent_edit.status_code == 409 and concurrent_edit.json()['error']['code'] == 'PUBLICATION_DRAFT_CONFLICT'
    assert commit(client, first, p1).status_code == 200
    failure = commit(client, second, p2); assert failure.status_code == 409 and failure.json()['error']['code'] == 'PUBLICATION_BASE_CHANGED'
    assert len(app.state.store.versions()) == 2
    third = edit(client, create(client)); p3 = preview(client, third)
    id = parsed['id']; d = get_draft(client, id); review = copy.deepcopy(d['reviewed']); review['property']['price'] = 79000000
    saved = save(client, id, d, review).json(); assert confirm(client, id, saved).status_code == 200
    fail = commit(client, third, p3); assert fail.status_code == 409 and fail.json()['error']['code'] == 'PUBLICATION_PREVIEW_STALE'
    p4 = preview(client, third); assert not p4['blockers']; assert commit(client, third, p4).status_code == 200
    assert app.state.store.latest()['property']['price'] == v1['property']['price']


def test_duplicate_upload_explicit_identity_and_cancel_leave_v1(client):
    _, parsed = upload_parse(client); v1 = confirm_publish(client, parsed); id = parsed['id']; cid = v1['document_approvals'][id]
    from pathlib import Path
    content = Path('demo_documents/物件概要_demo.pdf').read_bytes(); sha = hashlib.sha256(content).hexdigest()
    listing = client.get('/api/admin/documents/duplicates', params={'sha256': sha}, auth=ADMIN).json(); assert listing[0]['id'] == id
    duplicate = client.post('/api/admin/documents', files={'file': ('別名.pdf', content, 'application/pdf')}, auth=ADMIN)
    assert duplicate.status_code == 409 and duplicate.json()['error']['code'] == 'DUPLICATE_FILE'
    reuse = client.post('/api/admin/documents', data={'duplicate_action': 'reuse', 'reuse_document_id': id, 'replaces_document_id': id, 'replaces_confirmation_id': cid}, files={'file': ('別名.pdf', content, 'application/pdf')}, auth=ADMIN)
    assert reuse.status_code == 200 and reuse.json()['id'] == id and reuse.json()['reused']
    separate = client.post('/api/admin/documents', data={'duplicate_action': 'separate', 'replaces_document_id': id, 'replaces_confirmation_id': cid}, files={'file': ('更新TEST.pdf', content, 'application/pdf')}, auth=ADMIN).json()
    assert separate['id'] != id and separate['usage'] == 'unclassified'
    # Cancel an upload before parse; original document and file evidence remain.
    r = client.post(f"/api/admin/documents/{separate['id']}/updates/cancel", auth=ADMIN); assert r.status_code == 200, r.text
    assert r.json()['update_cancelled'] and app.state.store.latest()['document_approvals'][id] == cid
    assert app.state.store.get('documents', id)['confirmation_id'] == cid
    d = get_draft(client, id); review = copy.deepcopy(d['reviewed']); review['property']['price'] = 78000000
    saved = save(client, id, d, review).json(); confirmed = confirm(client, id, saved).json()
    assert client.post(f'/api/admin/documents/{id}/updates/cancel', auth=ADMIN).status_code == 200
    record = app.state.store.get('documents', id); assert record['confirmation_id'] == cid and record['reviewed']['property']['price'] == 76900000
    draft = edit(client, create(client), [{'document_id': id, 'confirmation_id': confirmed['confirmation_id']}]); view = preview(client, draft)
    assert view['blockers'][0]['code'] == 'CANCELLED_REVISION'
    assert commit(client, draft, view).status_code == 409 and len(app.state.store.versions()) == 1
    assert client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()['property']['price'] == 76900000


def test_restore_revocation_dates_and_internal_approval_are_blockers(client):
    record = approved(client, '住宅購入基礎FAQ_demo.pdf'); v1 = publish_documents(client, [record['id']]).json()
    id = record['id']; oldcid = record['confirmation_id']
    client.post(f'/api/admin/documents/{id}/usage', json={'usage': 'internal', 'note': 'TEST明示撤回'}, auth=ADMIN)
    restore = edit(client, create(client, v1['version'])); view = preview(client, restore)
    assert view['blockers'][0]['code'] == 'UNCONFIRMED_DOCUMENT'
    assert commit(client, restore, view).status_code == 409
    client.post(f'/api/admin/documents/{id}/usage', json={'usage': 'customer', 'note': 'TEST再選択だけ'}, auth=ADMIN)
    reconfirm = client.post(f'/api/admin/documents/{id}/confirm', json={'usage': 'customer', 'reviewed': record['reviewed'], 'note': 'TEST現在の内容を再確認'}, auth=ADMIN)
    assert reconfirm.status_code == 200
    view = preview(client, restore); assert view['blockers'][0]['code'] == 'REVOKED_APPROVAL'
    assert app.state.store.version(v1['version'])['document_approvals'][id] == oldcid
    assert commit(client, restore, view).status_code == 409
    d = get_draft(client, id); review = copy.deepcopy(d['reviewed']); review['document']['valid_until'] = '2000-01-01'
    saved = save(client, id, d, review).json(); r = confirm(client, id, saved); assert r.status_code == 200
    expired = edit(client, create(client), [{'document_id': id, 'confirmation_id': r.json()['confirmation_id']}]); view = preview(client, expired)
    assert view['blockers'][0]['code'] == 'DOCUMENT_EXPIRED' and commit(client, expired, view).status_code == 409
    assert len(app.state.store.versions()) == 1


def test_no_rates_capability_is_warning_not_a_blanket_publication_block(client):
    record = approved(client, '住宅購入基礎FAQ_demo.pdf'); v1 = publish_documents(client, [record['id']]); assert v1.status_code == 200
    draft = edit(client, create(client)); view = preview(client, draft)
    assert not view['blockers'] and any(w['code'] == 'NO_RATES' for w in view['warnings'])
    assert view['capabilities']['faq'] and not view['capabilities']['mortgage']
    assert commit(client, draft, view).status_code == 200


def test_admin_auth_and_schema_no_preview_bypass(client):
    for path in ['/api/admin/publication-drafts', '/api/admin/versions', '/api/admin/documents/duplicates?sha256=x']:
        assert client.get(path).status_code == 401
        assert client.get(path, auth=STAFF).status_code == 401
    assert client.post('/api/admin/publication-drafts', json={}).status_code == 401
    assert client.post('/api/admin/publish', json={'document_ids': []}, auth=ADMIN).status_code == 409
    assert client.post('/api/admin/publish', json={'draft_id': 'TEST', 'draft_revision': 0, 'preview_token': 'TEST', 'idempotency_key': 'short'}, auth=ADMIN).status_code == 422
    draft = create(client)
    response = client.post(f"/api/admin/publication-drafts/{draft['id']}", json={'revision': 0, 'items': [{'document_id': 'TEST', 'confirmation_id': None, 'internal_unknown': 'TEST'}], 'note': 'TEST'}, auth=ADMIN)
    assert response.status_code == 422


def test_resuming_cancelled_update_does_not_overwrite_concurrent_permission_revocation(client, monkeypatch):
    _, parsed = upload_parse(client); v1 = confirm_publish(client, parsed)
    from pathlib import Path
    response = client.post('/api/admin/documents', data={'duplicate_action': 'separate', 'replaces_document_id': parsed['id'], 'replaces_confirmation_id': v1['document_approvals'][parsed['id']]}, files={'file': ('TEST競合更新.pdf', Path('demo_documents/物件概要_demo.pdf').read_bytes(), 'application/pdf')}, auth=ADMIN)
    assert response.status_code == 200
    id = response.json()['id']; assert client.post(f'/api/admin/documents/{id}/parse', auth=ADMIN).status_code == 200
    assert client.post(f'/api/admin/documents/{id}/updates/cancel', auth=ADMIN).status_code == 200
    original_save = app.state.documents.save_draft
    def revoke_then_save(*args, **kwargs):
        app.state.documents.set_usage(id, 'internal', 'TEST別画面が先に対客利用を撤回')
        return original_save(*args, **kwargs)
    monkeypatch.setattr(app.state.documents, 'save_draft', revoke_then_save)
    race = client.post(f'/api/admin/documents/{id}/revisions', json={'reason': 'TEST取消候補を再編集'}, auth=ADMIN)
    assert race.status_code == 409 and race.json()['error']['code'] == 'DRAFT_SOURCE_CHANGED'
    record = app.state.store.get('documents', id)
    assert record['usage'] == 'internal' and record['usage_epoch'] == 1 and record['update_cancelled']
    assert record['confirmation_id'] is None and record.get('draft') is None
    assert app.state.store.latest()['document_approvals'] == v1['document_approvals']


def test_internal_candidate_keeps_old_permission_but_form_and_publish_use_candidate_usage(client):
    _, parsed = upload_parse(client); v1 = confirm_publish(client, parsed); id = parsed['id']; cid = v1['document_approvals'][id]
    session = client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()
    headers = {'X-Session-Token': session['token']}
    d = get_draft(client, id); review = copy.deepcopy(d['reviewed']); review['property']['price'] = 78000000
    candidate = save(client, id, d, review, usage='internal').json()
    result = confirm(client, id, candidate); assert result.status_code == 200, result.text
    newcid = result.json()['confirmation_id']; assert newcid != cid
    assert result.json()['usage'] == 'customer' and result.json()['latest_revision_usage'] == 'internal'
    reopened = get_draft(client, id)
    assert reopened['usage'] == 'internal' and reopened['reviewed']['property']['price'] == 78000000
    unchanged = client.get(f"/api/sessions/{session['id']}", headers=headers)
    assert unchanged.status_code == 200 and unchanged.json()['property']['price'] == 76900000
    assert client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()['property']['price'] == 76900000
    draft = edit(client, create(client), [{'document_id': id, 'confirmation_id': newcid}]); view = preview(client, draft)
    assert view['blockers'][0]['code'] == 'CUSTOMER_USAGE_REQUIRED'
    assert commit(client, draft, view).status_code == 409 and len(app.state.store.versions()) == 1
    cancel = client.post(f'/api/admin/documents/{id}/updates/cancel', auth=ADMIN); assert cancel.status_code == 200, cancel.text
    restored = get_draft(client, id)
    record = app.state.store.get('documents', id)
    assert record['confirmation_id'] == cid and record['latest_revision_usage'] == 'customer'
    assert record['latest_revision_id'] == v1['document_revisions'][id]
    assert restored['usage'] == 'customer' and restored['reviewed']['property']['price'] == 76900000
    assert client.get(f"/api/sessions/{session['id']}", headers=headers).json()['property']['price'] == 76900000
    assert available_snapshot(app.state.store, app.state.store.latest())['property']['price'] == 76900000


def test_price_literal_conflict_blocks_preview_and_commit_without_changing_current_version(client):
    _, parsed = upload_parse(client); v1 = confirm_publish(client, parsed); id = parsed['id']
    raw, normalized = copy.deepcopy(parsed['raw']), copy.deepcopy(parsed['normalized'])
    original_version = copy.deepcopy(app.state.store.version(v1['version']))
    session = client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()
    headers = {'X-Session-Token': session['token']}
    d = get_draft(client, id); reviewed = copy.deepcopy(d['reviewed']); reviewed['property']['price'] = 78000000
    saved = save(client, id, d, reviewed).json(); candidate = confirm(client, id, saved)
    assert candidate.status_code == 200
    record = candidate.json()
    assert any('price: 76900000' in item['text'] for item in record['reviewed']['knowledge'])
    assert record['raw'] == raw and record['normalized'] == normalized
    draft = edit(client, create(client), [{'document_id': id, 'confirmation_id': record['confirmation_id']}]); view = preview(client, draft)
    assert view['blockers'][0]['code'] == 'SOURCE_PRICE_CONFLICT' and view['blockers'][0]['document_id'] == id
    assert '資料本文の価格と登録価格' in view['blockers'][0]['message']
    rejected = commit(client, draft, view)
    assert rejected.status_code == 409 and rejected.json()['error']['code'] == 'SOURCE_PRICE_CONFLICT'
    assert len(app.state.store.versions()) == 1 and app.state.store.version(v1['version']) == original_version
    assert client.get(f"/api/sessions/{session['id']}", headers=headers).json()['property']['price'] == 76900000
    assert client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()['property']['price'] == 76900000
    # Explicit TEST employee correction affects reviewed body only. No automatic rewrite.
    d = get_draft(client, id); corrected = copy.deepcopy(d['reviewed']); amend_test_price(corrected, 78000000)
    saved = save(client, id, d, corrected, note='TEST社員が価格変更と本文の修正を明示入力').json()
    approved = confirm(client, id, saved, note='TEST本文と登録価格の一致を社員確認').json()
    fresh = edit(client, create(client), [{'document_id': id, 'confirmation_id': approved['confirmation_id']}]); view = preview(client, fresh)
    assert not view['blockers']
    result = commit(client, fresh, view); assert result.status_code == 200, result.text
    assert result.json()['property']['price'] == 78000000
    assert approved['raw'] == raw and approved['normalized'] == normalized
    assert app.state.store.version(v1['version']) == original_version
    new = client.post('/api/sessions', json={'mode': 'text', 'property_id': 'No.15'}).json()
    from app.services.ai_evidence import tool_evidence
    raw_search = app.state.tools.execute(app.state.store.get('sessions', new['id']), 'search_property_knowledge', {'query': '価格'})
    evidence = tool_evidence(app.state.store, app.state.store.get('sessions', new['id']), 'search_property_knowledge', raw_search)
    assert evidence['items'] and all('price: 76900000' not in item['text'] for item in evidence['items'])
    assert any('price: 78000000' in item['text'] for item in evidence['items'])


def test_distinct_real_sdk_file_restore_preview_shows_resulting_price_without_inferred_replacement(client):
    _, parsed = upload_parse(client); v1 = confirm_publish(client, parsed); id = parsed['id']
    from io import BytesIO
    from reportlab.pdfgen import canvas
    body = BytesIO(); pdf = canvas.Canvas(body)
    original_property = parsed['normalized']['property']
    lines = [f"property_name: {original_property['property_name']}", 'lot: No.15', 'price: 77900000', 'effective_date: 2026-10-02', 'valid_until: 2026-10-15']
    # An ASCII TEST title avoids font substitution in this isolated PDF.
    # The price and title below are genuinely read by the installed SDK.
    lines[0] = 'property_name: TEST different-file restore property'
    for index, line in enumerate(lines): pdf.drawString(40, 760 - index * 25, line)
    pdf.save()
    uploaded = client.post('/api/admin/documents', data={'replaces_document_id': id, 'replaces_confirmation_id': v1['document_approvals'][id]}, files={'file': ('TEST差替復元.pdf', body.getvalue(), 'application/pdf')}, auth=ADMIN)
    assert uploaded.status_code == 200, uploaded.text
    new_id = uploaded.json()['id']; assert new_id != id
    parsed_new = client.post(f'/api/admin/documents/{new_id}/parse', auth=ADMIN); assert parsed_new.status_code == 200
    new_record = parsed_new.json(); assert new_record['sdk_version'] == '1.8.0' and new_record['normalized']['property']['price'] == 77900000
    confirmed = client.post(f'/api/admin/documents/{new_id}/confirm', json={'reviewed': new_record['normalized'], 'usage': 'customer', 'note': 'TEST新ファイルの実SDK抽出価格を社員確認'}, auth=ADMIN); assert confirmed.status_code == 200
    candidate = create(client)
    candidate = edit(client, candidate, [{'document_id': new_id, 'confirmation_id': confirmed.json()['confirmation_id'], 'replaces_document_id': id, 'replaces_confirmation_id': v1['document_approvals'][id]}])
    view = preview(client, candidate); assert len(view['replaced']) == 1 and not view['blockers']
    v2 = commit(client, candidate, view).json(); assert v2['property']['price'] == 77900000
    original_v1 = copy.deepcopy(app.state.store.version(v1['version'])); original_v2 = copy.deepcopy(app.state.store.version(v2['version']))
    restore = edit(client, create(client, v1['version'])); restoration = preview(client, restore)
    assert [item['document_id'] for item in restoration['added']] == [id]
    assert [item['document_id'] for item in restoration['removed']] == [new_id]
    assert not restoration['replaced']  # No filename-based or invented replacement relation.
    prices = [c for c in restoration['changes'] if c['label'] == '価格']
    assert prices == [{'document_id': None, 'label': '価格', 'before': 77900000, 'after': 76900000, 'level': 'publication'}]
    assert not restoration['blockers']
    v3_response = commit(client, restore, restoration); assert v3_response.status_code == 200, v3_response.text
    v3 = v3_response.json(); assert v3['version'] > v2['version'] and v3['property']['price'] == 76900000
    assert v3['publication_diff']['changes'] == restoration['changes']
    assert app.state.store.version(v1['version']) == original_v1 and app.state.store.version(v2['version']) == original_v2
