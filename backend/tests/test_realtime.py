from knowledge_fixtures import approve_fixture, stamp_session
"""TEST scripted sockets/HTTP only. No live microphone or Realtime acceptance.

Official contracts checked 2026-10-07:
https://developers.openai.com/api/docs/guides/voice-server-controls
https://developers.openai.com/api/docs/guides/voice-webrtc?voice-api=realtime
https://developers.openai.com/api/docs/guides/realtime-conversations
https://developers.openai.com/api/reference/resources/realtime/subresources/calls/methods/hangup
"""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.models.domain import AppError
from app.repositories.store import Store
from app.services.realtime import RealtimeService
from app.services.tools import ToolService


class TestSocket:
    __test__ = False

    def __init__(self, events=(), stay_open=False):
        self.events = iter(events)
        self.sent = []
        self.sent_after = []
        self.current_event = None
        self.stay_open = stay_open
        self.closed = False
        self.done = asyncio.Event()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            event = next(self.events)
        except StopIteration:
            if self.stay_open and not self.closed:
                await self.done.wait()
            raise StopAsyncIteration
        self.current_event = event.get('type')
        return json.dumps(event)

    async def send(self, value):
        event = json.loads(value)
        self.sent.append(event)
        self.sent_after.append((self.current_event, event))

    async def close(self):
        self.closed = True
        self.done.set()


@pytest.fixture
def system(tmp_path):
    store = Store(tmp_path / 'realtime-test.db')
    store.init()
    for version, price in [(1, 76900000), (2, 77000000)]:
        snapshot = {
            'published_at': '2026-10-07T12:00:00+09:00',
            'property': {'property_name': f'TEST公開版{version} No.15', 'lot': 'No.15', 'price': price, 'valid_until': '2099-12-31'},
            'references': [{'document_id': f'TEST-doc-{version}', 'filename': f'TEST公開版{version}.pdf'}],
            'knowledge': [], 'faq': [], 'rates': [],
        }
        snapshot = approve_fixture(store, snapshot)
        with store.connect() as db:
            db.execute('INSERT INTO versions(version,payload) VALUES (?,?)', (version, json.dumps(snapshot, ensure_ascii=False)))
    session = {'id': 'TEST-session', 'version': 1, 'status': 'active', 'realtime': {'status': 'not_started'}}
    session.setdefault('property_id', 'No.15')
    stamp_session(store, session)
    settings = SimpleNamespace(api_key='TEST-no-network-key', realtime_model='TEST-realtime-model')
    service = RealtimeService(store, ToolService(store), settings)
    hangups = []

    async def hangup(call_id):
        hangups.append(call_id)
        return 200

    service.hangup = hangup
    return store, session, service, settings, hangups


def connection(session, socket, active=True):
    return {
        'socket': socket, 'session': session, 'call_id': 'rtc_TEST', 'greeted': False,
        'seen': set(), 'turns': 0, 'tool_count': 0, 'references': [],
        'active_response': active, 'pending_response': None, 'continue_tools': False,
    }


def test_tool_output_waits_for_response_done_and_uses_pinned_version(system):
    store, session, service, _, hangups = system
    socket = TestSocket([
        {'type': 'response.function_call_arguments.done', 'call_id': 'TEST-call', 'name': 'get_property_overview', 'arguments': '{}'},
        {'type': 'response.done', 'response': {'status': 'completed'}},
    ])
    value = connection(session, socket)
    service.connections[session['id']] = value
    asyncio.run(service.listen(value))
    assert [event['type'] for event in socket.sent] == ['conversation.item.create', 'response.create']
    assert socket.sent_after[1][0] == 'response.done'
    output = json.loads(socket.sent[0]['item']['output'])
    assert output['version'] == 1
    assert output['property']['price'] == 76900000
    assert hangups == ['rtc_TEST']
    assert not service.connections


def test_duplicate_tool_event_does_not_duplicate_business_action(system):
    store, session, service, _, _ = system
    call = {'type': 'response.function_call_arguments.done', 'call_id': 'TEST-staff-call', 'name': 'call_staff', 'arguments': json.dumps({'reason': 'TEST相談', 'last_customer_question': 'TEST質問'})}
    socket = TestSocket([call, call, {'type': 'response.done', 'response': {'status': 'completed'}}])
    value = connection(session, socket)
    asyncio.run(service.listen(value))
    assert len(store.list('staff_calls')) == 1
    assert len([e for e in socket.sent if e['type'] == 'conversation.item.create']) == 1
    assert value['tool_count'] == 1


def test_loan_judgment_transcript_triggers_real_staff_and_policy_response(system):
    store, session, service, _, _ = system
    question = '年収500万円なら絶対ローン通りますか？'
    socket = TestSocket([{'type': 'conversation.item.input_audio_transcription.completed', 'transcript': question}])
    value = connection(session, socket, active=False)
    asyncio.run(service.listen(value))
    calls = store.list('staff_calls')
    assert len(calls) == 1 and calls[0]['status'] == 'pending'
    assert calls[0]['last_customer_question'] == question
    create = [e for e in socket.sent if e['type'] == 'response.create'][0]
    assert '融資可否の判断をしない' in create['response']['instructions']
    assert '確定的なご案内はできません' in create['response']['instructions']
    assert [e['role'] for e in store.events(session['id']) if e['kind'] == 'message'] == ['user']


def test_loan_tool_error_is_not_success_output(system):
    _, session, service, _, _ = system
    socket = TestSocket([
        {'type': 'response.function_call_arguments.done', 'call_id': 'TEST-loan', 'name': 'calculate_mortgage', 'arguments': json.dumps({'down_payment': 5000000, 'years': 35, 'rate_id': 'unknown'})},
        {'type': 'response.done', 'response': {'status': 'completed'}},
    ])
    asyncio.run(service.listen(connection(session, socket)))
    output = json.loads(socket.sent[0]['item']['output'])
    assert output['error']['code'] == 'RATE_NOT_FOUND'
    assert 'monthly_payment' not in output


def test_failed_response_does_not_automatically_retry_and_sanitizes_status(system):
    store, session, service, _, hangups = system
    socket = TestSocket([{'type': 'response.done', 'response': {'status': 'failed', 'status_details': {'error': {'message': '/private/TEST secret'}}}}])
    value = connection(session, socket)
    value['continue_tools'] = True
    service.connections[session['id']] = value
    asyncio.run(service.listen(value))
    assert socket.sent == []
    status = store.get('sessions', session['id'])['realtime']
    assert status['status'] == 'error'
    assert status['error']['code'] == 'REALTIME_RESPONSE_FAILED'
    assert 'secret' not in json.dumps(status)
    assert hangups == ['rtc_TEST']


def test_protocol_error_closes_control_before_subsequent_transcript(system):
    store, session, service, _, hangups = system
    socket = TestSocket([
        {'type': 'error', 'error': {'message': '/private/TEST secret'}},
        {'type': 'conversation.item.input_audio_transcription.completed', 'transcript': 'これは処理されないTEST発話'},
    ])
    value = connection(session, socket)
    service.connections[session['id']] = value
    asyncio.run(service.listen(value))
    assert socket.sent == []
    assert socket.closed
    assert hangups == ['rtc_TEST']
    status = store.get('sessions', session['id'])['realtime']
    assert status['error']['code'] == 'REALTIME_PROTOCOL'
    assert 'secret' not in json.dumps(status)
    assert not [e for e in store.events(session['id']) if e['kind'] == 'message']


def test_ended_session_cannot_create_staff_from_voice_tool(system):
    store, session, service, _, _ = system
    store.put('sessions', dict(session, status='ended'))
    socket = TestSocket([{'type': 'response.function_call_arguments.done', 'call_id': 'TEST-ended', 'name': 'call_staff', 'arguments': json.dumps({'reason': 'TEST相談', 'last_customer_question': ''})}])
    asyncio.run(service.listen(connection(session, socket)))
    assert json.loads(socket.sent[0]['item']['output'])['error']['code'] == 'SESSION_ENDED'
    assert store.list('staff_calls') == []


def test_missing_key_is_explicit_and_no_connection_created(system):
    _, session, service, settings, hangups = system
    settings.api_key = ''
    with pytest.raises(AppError) as exc:
        asyncio.run(service.connect(session, 'v=0\r\nTEST'))
    assert exc.value.code == 'OPENAI_NOT_CONFIGURED'
    assert exc.value.status == 503
    assert service.connections == {} and service.connecting == set()
    assert hangups == []


def test_greeting_is_idempotent_and_deferred_during_active_response(system):
    _, session, service, _, _ = system
    socket = TestSocket()
    value = connection(session, socket, active=False)
    service.connections[session['id']] = value

    async def run():
        await service.greet(session['id'])
        await service.greet(session['id'])

    asyncio.run(run())
    assert len(socket.sent) == 1
    assert socket.sent[0]['type'] == 'response.create'
    assert socket.sent[0]['response']['tool_choice'] == 'none'
    assert '住宅購入' in socket.sent[0]['response']['instructions']
    assert value['greeted']


def test_connect_http429_has_one_attempt_and_no_socket(system, monkeypatch):
    import app.services.realtime as realtime_module
    store, session, service, _, _ = system
    original_client = httpx.AsyncClient
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(429, json={'error': {'message': '/private/TEST secret'}})

    monkeypatch.setattr(realtime_module.httpx, 'AsyncClient', lambda *args, **kwargs: original_client(*args, **kwargs, transport=httpx.MockTransport(handler)))

    async def forbidden_socket(*args, **kwargs):
        pytest.fail('TEST: socket must not be opened after HTTP429')

    monkeypatch.setattr(realtime_module.websockets, 'connect', forbidden_socket)
    with pytest.raises(AppError) as exc:
        asyncio.run(service.connect(session, 'v=0\r\nTEST'))
    assert exc.value.code == 'REALTIME_HTTP_429'
    assert len(requests) == 1
    assert service.connections == {} and service.connecting == set()
    assert 'secret' not in json.dumps(store.get('sessions', session['id'])['realtime'])


@pytest.mark.parametrize('transcript,allowed', [('35年でお願いします', False), ('フラット35でお願いします', True)])
def test_voice_tool_requires_actual_customer_transcript_product_choice(system, transcript, allowed):
    store, session, service, _, _ = system
    snapshot = store.version(1)
    snapshot['rates'] = [{'id': 'flat35', 'product': 'フラット35', 'rate_type': '全期間固定',
        'rate': 3.83, 'rate_over_90_percent': 3.94, 'effective_date': '2000-01-01', 'valid_until': '2099-12-31',
        'years_min': 21, 'years_max': 35, 'loan_amount_min': 1000000, 'loan_amount_max': 120000000}]
    snapshot = approve_fixture(store, snapshot)
    with store.connect() as db:
        db.execute('UPDATE versions SET payload=? WHERE version=1', (json.dumps(snapshot),))
    stamp_session(store, session)
    socket = TestSocket([
        {'type': 'conversation.item.input_audio_transcription.completed', 'transcript': transcript},
        {'type': 'response.function_call_arguments.done', 'call_id': 'TEST-choice', 'name': 'calculate_mortgage',
         'arguments': json.dumps({'down_payment': 5000000, 'years': 35, 'rate_id': 'flat35'})},
        {'type': 'response.done', 'response': {'status': 'completed'}},
    ])
    asyncio.run(service.listen(connection(session, socket, active=False)))
    item = next(e for e in socket.sent if e.get('item', {}).get('type') == 'function_call_output')
    result = json.loads(item['item']['output'])
    if allowed:
        assert result['mortgage']['monthly_payment'] == 315773
    else:
        assert result['error']['code'] == 'RATE_CONFIRMATION_REQUIRED'
        assert not any(e.get('name') == 'calculate_mortgage' for e in store.events(session['id']))


def test_explicit_close_hangs_up_before_closing_sideband(system):
    store, session, service, _, _ = system
    socket = TestSocket(stay_open=True)

    async def hangup(call_id):
        assert call_id == 'rtc_TEST'
        assert not socket.closed
        assert store.get('sessions', session['id'])['realtime']['status'] == 'closing'
        return 200

    service.hangup = hangup

    async def run():
        value = connection(session, socket, active=False)
        service.connections[session['id']] = value
        value['task'] = asyncio.create_task(service.listen(value))
        await service.close(session['id'])

    asyncio.run(run())
    assert socket.closed
    assert not service.connections
    assert store.get('sessions', session['id'])['realtime'] == {'status': 'closed', 'upstream_hangup_status': 200}


def test_connect_is_cancelled_if_session_ends_during_http(system, monkeypatch):
    import app.services.realtime as realtime_module
    store, session, service, _, hangups = system
    original_client = httpx.AsyncClient

    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        socket = TestSocket(stay_open=True)

        async def handler(request):
            started.set()
            await release.wait()
            return httpx.Response(200, text='v=0\r\nTEST-answer', headers={'Location': '/v1/realtime/calls/rtc_TEST'})

        async def open_socket(*args, **kwargs):
            return socket

        monkeypatch.setattr(realtime_module.httpx, 'AsyncClient', lambda *args, **kwargs: original_client(*args, **kwargs, transport=httpx.MockTransport(handler)))
        monkeypatch.setattr(realtime_module.websockets, 'connect', open_socket)
        pending = asyncio.create_task(service.connect(session, 'v=0\r\nTEST-offer'))
        await started.wait()
        await service.close(session['id'])
        store.put('sessions', dict(session, status='ended'))
        release.set()
        try:
            with pytest.raises(AppError) as exc:
                await pending
            assert exc.value.code == 'SESSION_ENDED'
            assert session['id'] not in service.connections
            assert hangups == ['rtc_TEST']
        finally:
            # Test cleanup must also work while reproducing the pre-fix race.
            if session['id'] in service.connections:
                await service.close(session['id'])

    asyncio.run(run())

@pytest.mark.parametrize('text',['御社の営業時間は何時ですか？','この年収ならローン審査に絶対通りますか？'])
def test_policy_reply_does_not_reuse_previous_property_sources(system,text):
    store,session,service,_,_=system
    session['property_id']=None;store.put('sessions',session)
    socket=TestSocket([{'type':'conversation.item.input_audio_transcription.completed','transcript':text}])
    value=connection(session,socket,active=False)
    value['references']=[{'document_id':'TEST-old-property','filename':'TEST old property.pdf'}]
    asyncio.run(service.listen(value))
    assert value['references']==[]
    assert any(e['type']=='response.create' for e in socket.sent)


@pytest.mark.parametrize('task', ['', '確認済み方針説明だけを読み上げてください', '融資可否の判断をしない', '公開版データ: {}'])
def test_every_response_keeps_japanese_style_and_business_rules(system, task):
    from app.services.ai import VOICE_STYLE, INSTRUCTIONS
    _, session, service, _, _ = system
    socket = TestSocket()
    value = connection(session, socket, active=False)
    asyncio.run(service.request_response(value, {'instructions': task}))
    prompt = socket.sent[0]['response']['instructions']
    assert VOICE_STYLE in prompt and INSTRUCTIONS in prompt
    assert task in prompt
    assert '月返済額を自分で計算しない' in prompt


def test_voice_configuration_rejects_unknown_and_accepts_candidates():
    from app.config import validated_realtime_voice
    for voice in ['marin', 'cedar', 'coral']:
        assert validated_realtime_voice(voice) == voice
    with pytest.raises(RuntimeError):
        validated_realtime_voice('not-a-supported-voice')
