"""R2 isolated, owned TEST material. No normal documents or real secrets."""
import copy
import json
from app.models.domain import now

PRIVATE = 'TEST_R2_INTERNAL_LEGAL_TEXT'
UNCLASSIFIED = 'TEST_R2_UNCLASSIFIED_LEGAL_TEXT'
PUBLIC = 'TEST_R2_PUBLIC_FACT'
TAIL = 'TEST末尾条件：契約前の確認であり、審査の承認を意味しません。'
URL = 'https://www.mlit.go.jp/totikensangyo/const/1_6_bf_000013.html'


def review(scope, marker=PUBLIC, *, property_doc=False, rate_doc=False):
    meta = {'scope': scope, 'source_name': 'TEST自有資料', 'source_url': URL,
            'checked_at': '2026-10-07', 'effective_date': '2000-01-01', 'valid_until': '2099-12-31'}
    out = {'document': meta, 'property': {}, 'knowledge': [], 'faq': [], 'rates': []}
    if property_doc:
        out['property'] = {'property_name': 'TEST住宅 No.15', 'lot': 'No.15', 'price': 76900000,
            'station': 'TEST駅', 'walking_minutes': 10, 'layout': 'TEST 3LDK', 'equipment': ['TEST設備'],
            'scope_notes': marker + ' 徒歩距離は分譲全体の範囲',
            **{k: meta[k] for k in ('source_name', 'source_url', 'checked_at', 'effective_date', 'valid_until')}}
    if rate_doc:
        out['rates'] = [{'bank': 'TEST銀行', 'product': 'TEST変動金利', 'rate_type': '変動', 'rate': 1.195,
            'years_min': 1, 'years_max': 35, 'loan_amount_min': 1000000, 'loan_amount_max': 100000000,
            'notes': marker + ' TEST審査・利用条件を満たす方。' + TAIL,
            'conditions': ['TEST公開条件'], **{k: meta[k] for k in ('source_name', 'source_url', 'checked_at', 'effective_date', 'valid_until')}}]
    else:
        out['knowledge'] = [{'text': marker + ' 住宅購入は希望と予算を整理します。' + 'TEST確認事項。' * 110 + TAIL}]
        out['faq'] = [{'question': '住宅購入で確認することは？', 'answer': marker + ' 契約前に重要事項説明を確認します。' + TAIL}]
    return out


def seed_pending(store):
    store.init()
    definitions = [
        ('A-general', 'general', PUBLIC, False, False),
        ('A-company', 'company', PUBLIC, False, False),
        ('A-property', 'property', PUBLIC, True, False),
        ('A-rates', 'general', PUBLIC, False, True),
        ('B-company', 'company', PRIVATE, False, False),
        ('B-property', 'property', PRIVATE, True, False),
        ('B-rates', 'general', PRIVATE, False, True),
        ('C-general', 'general', UNCLASSIFIED, False, False),
        ('C-property', 'property', UNCLASSIFIED, True, False),
        ('C-rates', 'general', UNCLASSIFIED, False, True),
    ]
    for id, scope, marker, prop, rate in definitions:
        if any(d['id'] == id for d in store.list('documents')): continue
        data = review(scope, marker, property_doc=prop, rate_doc=rate)
        store.put('documents', {'id': id, 'filename': 'TEST_' + id + '.pdf', 'status': 'parsed',
            'usage': 'unclassified', 'created_at': now(), 'parsed_at': now(), 'confirmed_at': None,
            'raw': {'TEST_fixture': True, 'text': marker}, 'normalized': copy.deepcopy(data),
            'sdk_api': 'TEST fixture; SDK not invoked', 'sdk_version': '1.8.0'})


def confirm_materials(documents):
    for record in documents.store.list('documents'):
        usage = 'customer' if record['id'].startswith('A-') else 'internal' if record['id'].startswith('B-') else 'unclassified'
        documents.confirm(record['id'], copy.deepcopy(record['normalized']), 'TEST实际用途与内容确认', usage, 'admin')
    return documents.publish(['A-general', 'A-company', 'A-property', 'A-rates'])


def poison_merged_version(store, version):
    """Simulate historic source merging. Approved source facts must win, not raw fields."""
    snapshot = store.version(version)
    snapshot['property']['property_name'] = PRIVATE
    snapshot['property']['scope_notes'] = PRIVATE
    snapshot['property']['price'] = 12345678
    snapshot['rates'][0]['notes'] = PRIVATE
    for record in store.list('documents'):
        if record['id'].startswith('A-'): continue
        snapshot['document_ids'].append(record['id'])
        snapshot['document_approvals'][record['id']] = record['confirmation_id']
        for section in ('knowledge', 'faq', 'rates'):
            snapshot[section].extend(dict(item, scope=record['reviewed']['document']['scope']) for item in record['reviewed'][section])
    with store.connect() as db:
        db.execute('UPDATE versions SET payload=? WHERE version=?', (json.dumps(snapshot, ensure_ascii=False), version))
    return snapshot
