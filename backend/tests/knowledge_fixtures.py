"""Explicit TEST source approvals for pre-existing unit fixtures, never runtime.

Tests that used handwritten snapshots now need immutable source confirmations.
Pure mortgage tests keep their original snapshots/formula assertions.
"""
import copy
import json
from app.services.knowledge_access import permission_stamp


def approve_fixture(store, snapshot):
    s = copy.deepcopy(snapshot)
    docs = {}
    prop_id = next((r.get('document_id') for r in s.get('references', []) if r.get('document_id')), 'TEST-property')
    def review(doc, scope):
        return docs.setdefault(doc, {'document': {'scope': scope, 'source_url': '', 'source_name': 'TEST approved source', 'checked_at': '2026-10-07', 'effective_date': '2000-01-01', 'valid_until': '2099-12-31'}, 'property': {}, 'knowledge': [], 'faq': [], 'rates': []})
    if s.get('property'):
        p = copy.deepcopy(s['property']); p.pop('field_references', None)
        p.setdefault('effective_date', '2000-01-01'); p.setdefault('valid_until', '2099-12-31')
        reference = next((r for r in s.get('references', []) if r.get('document_id') == prop_id), {})
        p.setdefault('source_url', reference.get('source_url', ''))
        review(prop_id, 'property')['property'] = p
    for section in ('knowledge', 'faq', 'rates'):
        for i, raw in enumerate(s.get(section, [])):
            item = copy.deepcopy(raw); ref = item.setdefault('reference', {})
            doc = ref.get('document_id') or (f'TEST-rate-{i}' if section == 'rates' else prop_id)
            ref['document_id'] = doc
            scope = item.get('scope', 'general' if section == 'rates' else 'property')
            if section == 'rates':
                item.setdefault('bank', 'TEST銀行'); item.setdefault('rate_type', 'TEST固定'); item.setdefault('notes', 'TEST条件')
            r = review(doc, scope); r[section].append(item)
            r['document']['source_url'] = ref.get('source_url', '')
    s['document_ids'] = list(docs); s['document_approvals'] = {}
    for doc, r in docs.items():
        record = {'id': doc, 'filename': 'TEST-source.pdf', 'status': 'published', 'usage': 'customer', 'reviewed': r, 'confirmed_at': '2026-10-07', 'raw': {'TEST': True}, 'normalized': r}
        proof = {'event': 'business_confirmation', 'usage': 'customer', 'actor': 'admin', 'confirmed_at': record['confirmed_at'], 'reviewed': r}
        with store.connect() as db:
            cursor = db.execute('INSERT INTO confirmations(document_id,payload) VALUES (?,?)', (doc, json.dumps(proof, ensure_ascii=False)))
            record['confirmation_id'] = cursor.lastrowid
        store.put('documents', record); s['document_approvals'][doc] = record['confirmation_id']
    return s


def stamp_session(store, session):
    from app.services.context import raw_snapshot_for
    session.update(knowledge_boundary=2, permission_stamp=permission_stamp(store, raw_snapshot_for(store, session)))
    store.put('sessions', session)
    return session
