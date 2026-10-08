from knowledge_fixtures import approve_fixture
"""Synthetic R1 fixture / deterministic TEST provider. Never calls a paid API."""
import copy
import json
from app.models.domain import now
from app.services.context import observe_customer

MARKER = 'TEST_INTERNAL_R1_DO_NOT_RETURN'
UNKNOWN = {'internal_note': MARKER, 'debug_payload': {'future_nested_key': MARKER}, 'new_unlisted_field': MARKER}


def snapshot():
    reference = dict(document_id='TEST-property', filename=MARKER + '.pdf', location=MARKER,
                     source_url='https://www.sekisuihouse.co.jp/bunjou/1/12221/b350007/s357006/00015123/06top.html', **UNKNOWN)
    rate_ref = dict(reference, document_id='TEST-rate', source_url='https://www.bk.mufg.jp/kariru/jutaku/yuuguu/index.html')
    general_ref = dict(reference, document_id='TEST-general', source_url='https://www.mlit.go.jp/totikensangyo/const/1_6_bf_000013.html')
    return {
        **copy.deepcopy(UNKNOWN), 'published_at': now(), 'document_ids': ['TEST-property', 'TEST-rate', 'TEST-general'],
        'property': dict(UNKNOWN, property_name='TEST住宅 No.15', lot='No.15', price=76900000,
                         address='TEST展示住所', land_area=130.7, building_area=93.25, layout='TEST 3LDK',
                         station='TEST駅', walking_minutes=10, equipment=['TEST設備'], surroundings=['TEST公園'],
                         scope_notes='TEST徒歩距離は分譲全体の範囲', field_references={'price': rate_ref, 'station': reference, 'unknown': UNKNOWN},
                         checked_at='2026-10-07', effective_date='2000-01-01', valid_until='2099-12-31'),
        'rates': [dict(UNKNOWN, id='TEST-mufg', bank='三菱UFJ銀行', product='TEST変動金利', rate_type='変動',
                       rate=1.195, effective_date='2000-01-01', valid_until='2099-12-31',
                       years_min=1, years_max=35, loan_amount_min=1000000, loan_amount_max=100000000,
                       notes='TEST審査・利用条件を満たす方。参考金利です。', conditions=['TEST公開条件'], reference=rate_ref)],
        'knowledge': [dict(UNKNOWN, text='TEST住宅購入では希望と予算を整理し、重要事項説明を確認します。', scope='general', reference=general_ref),
                      dict(UNKNOWN, text='TEST設備は確認済みの資料を参照してください。', scope='property', reference=reference)],
        'faq': [dict(UNKNOWN, question='TEST未検索FAQ', answer='TEST FAQ_COLLECTION_NOT_REQUESTED', scope='general', reference=general_ref)],
        'references': [reference, rate_ref, general_ref],
        'document_validity': {key: dict(UNKNOWN, scope=scope, effective_date='2000-01-01', valid_until='2099-12-31')
                              for key, scope in [('TEST-property', 'property'), ('TEST-rate', 'general'), ('TEST-general', 'general')]},
    }


def seed(store):
    store.init()
    with store.connect() as db:
        if not db.execute('SELECT 1 FROM versions').fetchone():
            db.execute('INSERT INTO versions(payload) VALUES (?)', (json.dumps(approve_fixture(store, snapshot()), ensure_ascii=False),))
    store.put('documents', {'id': 'TEST-unpublished', 'status': 'parsed', 'raw': UNKNOWN,
                           'normalized': dict(property={'property_name': 'TEST_UNPUBLISHED_PROPERTY'}), 'reviewed': UNKNOWN})


class TestProvider:
    """Conversation fixture for HTTP/UI validation, not a real AI or mic test."""
    __test__ = False
    def __init__(self, store, tools): self.store, self.tools = store, tools

    async def respond(self, record, question):
        self.store.event(record['id'], 'message', dict(UNKNOWN, role='user', text=question, channel='text', created_at=now()))
        record = observe_customer(self.store, record, question)
        if '紹介' in question:
            name, args, answer = 'list_properties', {}, 'TEST: 公開済みのサンプルをご案内します。'
        elif 'No.15' in question:
            name, args, answer = 'get_property_overview', {}, 'TEST: No.15の価格は7690万円です。TEST設備が掲載されています。'
        elif 'ローン' in question:
            name, args, answer = 'get_mortgage_rates', {}, 'TEST: 公開済み参考金利の商品を選択してください。'
        else:
            name, args, answer = 'search_consultation_knowledge', {'query': '住宅購入', 'scope': 'general'}, 'TEST: 住宅購入では希望と予算を整理します。'
        raw = self.tools.execute(record, name, args)
        refs = raw.get('references', [])
        self.store.event(record['id'], 'message', dict(UNKNOWN, role='assistant', text=answer, channel='text', created_at=now(),
                                                     references=refs, tool_results=[dict(UNKNOWN, name=name, result=raw)]))
        return dict(UNKNOWN, answer=answer, references=refs, tool_results=[dict(UNKNOWN, name=name, result=raw)],
                    version=record['version'], snapshot=snapshot())


class PoisonTools:
    """Inject unknowns in *actual route service results* and stored tool events."""
    def __init__(self, tools): self.inner, self.staff = tools, tools.staff

    def execute(self, *args, **kwargs):
        result = self.inner.execute(*args, **kwargs)
        result.update(copy.deepcopy(UNKNOWN))
        # Store.event copies JSON; poison the stored event separately for polling.
        with self.inner.store.connect() as db:
            row = db.execute("SELECT id,payload FROM events WHERE session_id=? AND kind='tool' ORDER BY id DESC LIMIT 1", (args[0]['id'],)).fetchone()
            if row:
                payload = json.loads(row['payload']); payload.update(copy.deepcopy(UNKNOWN))
                payload['arguments'].update(copy.deepcopy(UNKNOWN)); payload['result'].update(copy.deepcopy(UNKNOWN))
                db.execute('UPDATE events SET payload=? WHERE id=?', (json.dumps(payload, ensure_ascii=False), row['id']))
        return result
