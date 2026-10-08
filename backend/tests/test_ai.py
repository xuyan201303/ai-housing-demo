from knowledge_fixtures import approve_fixture, stamp_session
"""TEST-only scripted provider responses. These are not live AI acceptance."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.models.domain import AppError
from app.repositories.store import Store
from app.services.ai import AiService
from app.services.sessions import SessionService
from app.services.tools import ToolService


@pytest.fixture
def system(tmp_path):
    store = Store(tmp_path / 'ai-tests.db')
    store.init()
    for version, price, knowledge in [(1, 76900000, 'TEST旧版: 床暖房あり'), (2, 77000000, 'TEST新版だけの秘密: 更新済み')]:
        snapshot = {
            'published_at': '2026-10-07T12:00:00+09:00',
            'property': {'property_name': 'TEST物件 No.15', 'lot': 'No.15', 'price': price, 'valid_until': '2099-12-31'},
            'references': [{'document_id': f'doc-{version}', 'filename': f'TEST公開版{version}.pdf'}],
            'knowledge': [{'text': knowledge, 'reference': {'document_id': f'doc-{version}', 'filename': f'TEST公開版{version}.pdf'}}],
            'faq': [], 'rates': [],
        }
        snapshot = approve_fixture(store, snapshot)
        with store.connect() as db:
            db.execute('INSERT INTO versions(version,payload) VALUES (?,?)', (version, json.dumps(snapshot, ensure_ascii=False)))
    store.put('documents', {'id': 'unpublished', 'status': 'parsed', 'raw': 'TEST_UNPUBLISHED_RAW_SECRET'})
    session = {'id': 'test-session', 'version': 1, 'status': 'active'}
    session.setdefault('property_id', 'No.15')
    stamp_session(store, session)
    settings = SimpleNamespace(api_key='TEST-only-key-never-sent-over-network', text_model='TEST-scripted-model')
    service = AiService(store, ToolService(store), settings)
    return store, session, service, settings


def scripted_transport(monkeypatch, script):
    """Intercept all AsyncClient requests; every response is explicit TEST data."""
    import app.services.ai as ai_module
    original_client = httpx.AsyncClient
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        item = script[min(len(requests) - 1, len(script) - 1)]
        if isinstance(item, Exception):
            raise item
        status, payload = item
        return httpx.Response(status, json=payload)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(ai_module.httpx, 'AsyncClient', lambda *args, **kwargs: original_client(*args, **kwargs, transport=transport))
    return requests


def message(text):
    return {'output': [{'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': text}]}]}


def function(name, arguments, call_id='test-call'):
    return {'output': [{'type': 'function_call', 'name': name, 'arguments': json.dumps(arguments), 'call_id': call_id}]}


def test_missing_key_reports503_and_logs_customer_only(system):
    store, session, service, settings = system
    settings.api_key = ''
    with pytest.raises(AppError) as exc:
        asyncio.run(service.respond(session, '駅から何分ですか？'))
    assert exc.value.code == 'OPENAI_NOT_CONFIGURED'
    assert exc.value.status == 503
    events = store.events(session['id'])
    assert [(e['role'], e['text']) for e in events] == [('user', '駅から何分ですか？')]
    assert store.list('staff_calls') == []


def test_loan_judgment_uses_real_backend_handoff_without_provider(system, monkeypatch):
    store, session, service, _ = system
    requests = scripted_transport(monkeypatch, [(200, message('TEST must never be used'))])
    result = asyncio.run(service.respond(session, '年収500万円なら絶対ローン通りますか？'))
    assert requests == []
    assert result['provider'] == 'backend_policy'
    assert '確定的なご案内はできません' in result['answer']
    call = store.get('staff_calls', result['staff_call']['id'])
    assert call['status'] == 'pending'
    assert call['last_customer_question'] == '年収500万円なら絶対ローン通りますか？'
    messages = [e for e in store.events(session['id']) if e['kind'] == 'message']
    assert [e['role'] for e in messages] == ['user', 'assistant']
    assert messages[-1]['provider'] == 'backend_policy'


def test_http429_is_one_request_without_retry_or_fallback(system, monkeypatch):
    store, session, service, _ = system
    requests = scripted_transport(monkeypatch, [(429, {'error': {'message': 'TEST response detail must not be shown'}})])
    with pytest.raises(AppError) as exc:
        asyncio.run(service.respond(session, '設備を教えてください'))
    assert exc.value.code == 'OPENAI_HTTP_429'
    assert len(requests) == 1
    assert 'TEST response detail' not in exc.value.message
    assert not [e for e in store.events(session['id']) if e['kind'] == 'message' and e['role'] == 'assistant']


def test_controlled_tool_calls_use_pinned_published_version(system, monkeypatch):
    store, session, service, _ = system
    requests = scripted_transport(monkeypatch, [
        (200, function('search_property_knowledge', {'query': '床暖房'})),
        (200, message('TEST-scripted: 公開版1の資料に床暖房の記載があります。')),
    ])
    result = asyncio.run(service.respond(session, '床暖房がありますか？'))
    assert len(requests) == 2
    assert result['version'] == 1
    assert result['provider'] == 'openai'  # Transport is scripted TEST, not live acceptance.
    encoded = json.dumps(requests, ensure_ascii=False)
    assert '76900000' in encoded
    assert '77000000' not in encoded
    assert 'TEST新版だけの秘密' not in encoded
    assert 'TEST_UNPUBLISHED_RAW_SECRET' not in encoded
    assert result['tool_results'][0]['result']['version'] == 1
    assert {r['document_id'] for r in result['references']} == {'doc-1'}
    tool_events = [e for e in store.events(session['id']) if e['kind'] == 'tool']
    assert [e['name'] for e in tool_events] == ['get_consultation_context', 'search_property_knowledge']


def test_tool_error_is_returned_as_error_to_provider_and_customer(system, monkeypatch):
    store, session, service, _ = system
    requests = scripted_transport(monkeypatch, [
        (200, function('calculate_mortgage', {'down_payment': 5000000, 'years': 35, 'rate_id': 'unpublished-rate'})),
        (200, message('TEST-scripted: この公開版で金利を確認できません。スタッフへお尋ねください。')),
    ])
    result = asyncio.run(service.respond(session, 'ローン月額を知りたいです'))
    tool_result = result['tool_results'][0]['result']
    assert tool_result['error']['code'] == 'RATE_NOT_FOUND'
    assert 'monthly_payment' not in tool_result
    output = [item for item in requests[1]['input'] if item.get('type') == 'function_call_output'][0]
    assert json.loads(output['output'])['error']['code'] == 'RATE_NOT_FOUND'
    assert store.list('staff_calls') == []


def test_tool_loop_has_finite_upper_bound(system, monkeypatch):
    store, session, service, _ = system
    requests = scripted_transport(monkeypatch, [(200, function('get_property_overview', {}))])
    with pytest.raises(AppError) as exc:
        asyncio.run(service.respond(session, '物件について'))
    assert exc.value.code == 'TOOL_LIMIT'
    assert len(requests) == 6
    assert not [e for e in store.events(session['id']) if e['kind'] == 'message' and e['role'] == 'assistant']


def test_empty_response_is_error_without_fake_answer(system, monkeypatch):
    store, session, service, _ = system
    requests = scripted_transport(monkeypatch, [(200, {'output': []})])
    with pytest.raises(AppError) as exc:
        asyncio.run(service.respond(session, 'こんにちは'))
    assert exc.value.code == 'OPENAI_EMPTY_RESPONSE'
    assert len(requests) == 1
    assert not [e for e in store.events(session['id']) if e['kind'] == 'message' and e['role'] == 'assistant']


@pytest.mark.parametrize('question,allowed', [('35年でお願いします', False), ('フラット35でお願いします', True)])
def test_real_tool_boundary_requires_customer_product_choice(system, monkeypatch, question, allowed):
    store, session, service, _ = system
    snapshot = store.version(1)
    snapshot['rates'] = [{'id': 'flat35', 'product': 'フラット35', 'rate_type': '全期間固定',
        'rate': 3.83, 'rate_over_90_percent': 3.94, 'effective_date': '2000-01-01', 'valid_until': '2099-12-31',
        'years_min': 21, 'years_max': 35, 'loan_amount_min': 1000000, 'loan_amount_max': 120000000,
        'reference': {'filename': 'TEST rates.xlsx'}}]
    snapshot = approve_fixture(store, snapshot)
    with store.connect() as db:
        db.execute('UPDATE versions SET payload=? WHERE version=1', (json.dumps(snapshot),))
    stamp_session(store, session)
    scripted_transport(monkeypatch, [
        (200, function('calculate_mortgage', {'down_payment': 5000000, 'years': 35, 'rate_id': 'flat35'})),
        (200, message('TEST scripted reply after real tool boundary')),
    ])
    result = asyncio.run(service.respond(session, question))['tool_results'][0]['result']
    if allowed:
        assert result['monthly_payment'] == 315773
    else:
        assert result['error']['code'] == 'RATE_CONFIRMATION_REQUIRED'
        assert not any(e.get('name') == 'calculate_mortgage' for e in store.events(session['id']))
        # The explicit customer form remains usable independently of AI chat.
        assert service.tools.execute(session, 'calculate_mortgage', {'down_payment': 5000000, 'years': 35, 'rate_id': 'flat35'})['monthly_payment'] == 315773


def test_loan_next_turn_receives_fresh_pinned_ids_dates_not_only_prior_prose(system, monkeypatch):
    store, session, service, _ = system
    snapshot = store.version(1)
    snapshot['rates'] = [{'id': 'TEST-exact-doc-local-rate-id', 'product': 'フラット35', 'rate': 3.83,
        'effective_date': '2000-01-01', 'valid_until': '2099-12-31', 'reference': {'filename': 'TEST rates.xlsx'}}]
    snapshot = approve_fixture(store, snapshot)
    with store.connect() as db:
        db.execute('UPDATE versions SET payload=? WHERE version=1', (json.dumps(snapshot),))
    stamp_session(store, session)
    store.event(session['id'], 'message', {'role': 'user', 'channel': 'text', 'text': '住宅ローンを知りたい'})
    store.event(session['id'], 'message', {'role': 'assistant', 'channel': 'text', 'text': 'TEST prior prose has no structured ID'})
    requests = scripted_transport(monkeypatch, [(200, message('TEST scripted current-rate answer'))])
    asyncio.run(service.respond(session, '35年でお願いします'))
    controlled = next(item['content'] for item in requests[0]['input'] if item.get('role') == 'user' and 'current_rate_evidence' in item['content'])
    assert 'TEST-exact-doc-local-rate-id' in controlled
    assert '2099-12-31' in controlled
    assert not any(e.get('name') == 'calculate_mortgage' for e in store.events(session['id']))
