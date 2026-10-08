"""Document permission gate. Rebuild facts from immutable approved sources.

Published merged fields are an employee audit view, never Customer evidence.
No legacy inference from scope, URLs, parsed status or previous publication.
"""
import hashlib
import json
from datetime import date
from app.models.domain import AppError, now

BOUNDARY_VERSION = 2
RESTART_MESSAGE = '資料の利用権限を更新しました。この接客を終了し、新しい接客を開始してください。'


def approvals(store, snapshot):
    result = []
    declared = snapshot.get('document_approvals', {})
    if not isinstance(declared, dict): return result
    with store.connect() as db:
        for doc_id in snapshot.get('document_ids', []):
            confirmation_id = declared.get(doc_id)
            if not isinstance(confirmation_id, int) or isinstance(confirmation_id, bool): continue
            doc = db.execute('SELECT payload FROM documents WHERE id=?', (doc_id,)).fetchone()
            row = db.execute('SELECT payload FROM confirmations WHERE id=? AND document_id=?', (confirmation_id, doc_id)).fetchone()
            if not doc or not row: continue
            record, proof = json.loads(doc['payload']), json.loads(row['payload'])
            revision = db.execute('SELECT payload FROM document_revisions WHERE confirmation_id=? AND document_id=?', (confirmation_id, doc_id)).fetchone()
            association = json.loads(revision['payload']) if revision else None
            # A retained immutable confirmation is usable only within the same
            # explicit permission epoch. Regrant never revives a revoked proof.
            eligible = bool(association and not association.get('cancelled') and
                            association.get('usage_epoch', 0) == record.get('usage_epoch', 0))
            if not association:
                eligible = (record.get('confirmation_id') == confirmation_id and
                            proof.get('usage_epoch', 0) == record.get('usage_epoch', 0) and
                            (not record.get('usage_changed_at') or
                             record['usage_changed_at'] <= proof.get('confirmed_at', '')))
            if (record.get('usage', 'unclassified') != 'customer' or
                record.get('status') not in {'confirmed', 'published'} or not eligible or
                proof.get('event') != 'business_confirmation' or proof.get('usage') != 'customer' or
                not proof.get('confirmed_at') or not proof.get('actor')): continue
            result.append((doc_id, confirmation_id, proof))
    return result


def permission_stamp(store, snapshot):
    proofs = [(doc, cid) for doc, cid, _ in approvals(store, snapshot)]
    return hashlib.sha256(json.dumps(proofs, sort_keys=True).encode()).hexdigest()


def require_boundary(store, session, snapshot):
    if (session.get('knowledge_boundary') != BOUNDARY_VERSION or
        session.get('permission_stamp') != permission_stamp(store, snapshot)):
        raise AppError('SESSION_RESTART_REQUIRED', RESTART_MESSAGE, 409)


def evidence_revision(store, session):
    from app.services.context import raw_snapshot_for
    raw = raw_snapshot_for(store, session)
    require_boundary(store, session, raw)
    material = available_snapshot(store, raw)
    return hashlib.sha256(json.dumps(material, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def current(meta, today):
    try:
        return date.fromisoformat(meta['effective_date'][:10]) <= today <= date.fromisoformat(meta['valid_until'][:10])
    except (KeyError, TypeError, ValueError): return False


def available_snapshot(store, snapshot, today=None):
    """Source-level reconstruction; no values from legacy/merged fields survive."""
    today = today or date.fromisoformat(now()[:10])
    out = {'version': snapshot.get('version'), 'published_at': snapshot.get('published_at'), 'property': {}, 'knowledge': [], 'faq': [],
           'rates': [], 'references': [], 'document_ids': [], 'document_validity': {}, '_property_scope_conditions': []}
    property_sources = []
    for doc_id, _, proof in approvals(store, snapshot):
        review = proof.get('reviewed', {})
        scope = review.get('document', {}).get('scope', 'property')
        if scope not in {'general', 'company', 'property'}: continue
        meta = review.get('property', {}) if scope == 'property' else review.get('document', {})
        if scope == 'property' and review.get('property'): property_sources.append((doc_id, review['property']))
        # Both the source document and each individual product must be current.
        if not current(meta, today): continue
        ref = {'document_id': doc_id, 'source_url': meta.get('source_url', '')}
        out['document_ids'].append(doc_id)
        out['document_validity'][doc_id] = {k: meta.get(k) for k in ('effective_date', 'valid_until')}
        out['document_validity'][doc_id]['scope'] = scope
        out['references'].append(ref)
        for section in ('knowledge', 'faq', 'rates'):
            for item in review.get(section, []):
                if section == 'rates' and not current(item, today): continue
                # Validated confirmation assigns references to its own document.
                if item.get('reference', {}).get('document_id') != doc_id: continue
                out[section].append(dict(item, scope=scope))
        if scope == 'property':
            if isinstance(meta.get('scope_notes'), str) and meta['scope_notes'] not in out['_property_scope_conditions']:
                out['_property_scope_conditions'].append(meta['scope_notes'])
            for key, value in review.get('property', {}).items():
                previous = out['property'].get(key)
                if isinstance(value, list) and isinstance(previous, list):
                    value = list(dict.fromkeys(previous + value))
                elif previous is not None and previous != value and key not in {'source_url', 'source_name', 'checked_at', 'effective_date', 'valid_until', 'scope_notes'}:
                    raise AppError('CUSTOMER_SOURCE_CONFLICT', '物件資料の確認が必要です。スタッフへご相談ください。', 409)
                out['property'][key] = value
                out['property'].setdefault('field_references', {})[key] = ref
    # Single-property product: contradictory/expired contributing sources cannot
    # be combined into a partial valid price or silently renew another source.
    if property_sources:
        if any(not current(meta, today) for _, meta in property_sources):
            expired = any(str(meta.get('valid_until', ''))[:10] < today.isoformat() for _, meta in property_sources)
            out['_property_error'] = 'PROPERTY_EXPIRED' if expired else 'PROPERTY_NOT_YET_EFFECTIVE'
            out['property'] = {}
            out['knowledge'] = [i for i in out['knowledge'] if i['scope'] != 'property']
            out['faq'] = [i for i in out['faq'] if i['scope'] != 'property']
        elif out['property']:
            out['property']['valid_until'] = min(meta['valid_until'] for _, meta in property_sources)
            out['property']['effective_date'] = max(meta['effective_date'] for _, meta in property_sources)
    return out
