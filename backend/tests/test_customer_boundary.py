from knowledge_fixtures import approve_fixture
"""R1 actual HTTP outputs, isolated synthetic DB and TEST provider, no paid calls."""
import asyncio
import copy
import json
import socket
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.repositories.store import Store
from app.services.sessions import SessionService
from app.services.tools import ToolService
from app.services.realtime import RealtimeService
from app.services.context import observe_customer
from test_realtime import TestSocket, connection
from public_boundary_fixtures import MARKER, UNKNOWN, TestProvider, PoisonTools, seed, snapshot

ADMIN = ('admin', 'TEST-r1-admin')
STAFF = ('staff', 'TEST-r1-staff')


@pytest.fixture
def system(tmp_path, monkeypatch):
    # No normal DB initialization; all service objects replaced before lifespan.
    store = Store(tmp_path / 'R1-isolated.db'); seed(store)
    tools = PoisonTools(ToolService(store)); sessions = SessionService(store)
    monkeypatch.setattr(settings, 'api_key', '')
    monkeypatch.setattr(settings, 'admin_password', ADMIN[1]); monkeypatch.setattr(settings, 'staff_password', STAFF[1])
    for name, value in [('store', store), ('sessions', sessions), ('tools', tools), ('ai', TestProvider(store, tools)),
                        ('realtime', RealtimeService(store, tools, SimpleNamespace(api_key='', realtime_model='TEST-no-network')))]:
        monkeypatch.setattr(app.state, name, value)
    def forbidden(*a, **kw): raise AssertionError('R1 forbids outbound network')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, store, tools


def create(client, **values):
    response = client.post('/api/sessions', json={'mode': 'text', **values})
    assert response.status_code == 200, response.text
    value = response.json()
    return value, {'X-Session-Token': value['token']}


def safe(response, *, creation=False):
    assert response.status_code == 200, response.text
    payload = response.json()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert MARKER not in serialized
    def walk(value):
        if isinstance(value, dict):
            for k, v in value.items():
                assert k not in {'snapshot', 'knowledge', 'faq', 'raw', 'normalized', 'reviewed', 'tool_events', 'tool_results', 'arguments',
                                 'internal_note', 'debug_payload', 'new_unlisted_field', 'filename', 'location', 'source_url', 'field_references', 'scope_notes'}
                if k == 'token': assert creation
                walk(v)
        elif isinstance(value, list):
            for v in value: walk(v)
    walk(payload)
    return payload


def test_all_customer_http_exits_block_unknowns_without_removing_business(system, monkeypatch):
    client, store, tools = system
    # Poison start's service object itself, not just a projection unit test.
    original = app.state.sessions.start
    def poisoned_start(*a, **kw):
        record = original(*a, **kw); record.update(copy.deepcopy(UNKNOWN)); store.put('sessions', {k:v for k,v in record.items() if k!='snapshot'}); return record
    monkeypatch.setattr(app.state.sessions, 'start', poisoned_start)
    s = safe(client.post('/api/sessions', json={'mode':'text'}), creation=True); h={'X-Session-Token':s['token']}; path=f"/api/sessions/{s['id']}"
    assert s['property'] is None and s['products'][0]['rate'] == 1.195 and s['messages']==[]
    assert client.get('/api/property').status_code == 410
    answer = safe(client.post(path+'/messages', json={'text':'住宅購入は？'}, headers=h))
    assert answer['answer'].startswith('TEST:') and answer['display_events'][0]['items'][0]['scope']=='general'
    assert 'FAQ_COLLECTION_NOT_REQUESTED' not in json.dumps(answer)
    candidate = safe(client.post(path+'/messages', json={'text':'紹介できる物件は？'}, headers=h))
    assert candidate['display_events'][0]['properties']==[{'property_id':'No.15','property_name':'TEST住宅 No.15'}]
    picked = safe(client.post(path+'/property', json={'property_id':'No.15'}, headers=h))
    assert picked['property']['price']==76900000 and picked['property']['equipment']==['TEST設備']
    assert '分譲全体' in picked['property']['scope_notices'][0]
    assert picked['property']['references'][0]['url'].startswith('https://www.sekisuihouse.co.jp/')
    safe(client.post(path+'/messages', json={'text':'No.15の設備'}, headers=h))
    # Poison actual mortgage and staff route service outputs via PoisonTools.
    loan = safe(client.post(path+'/mortgage', json={'down_payment':5000000,'years':35,'rate_id':'TEST-mufg'}, headers=h))
    assert loan['monthly_payment']>0 and loan['annual_interest_rate']==1.195 and loan['conditions']==['TEST公開条件']
    call = safe(client.post(path+'/staff-calls', json={'reason':'TEST相談'}, headers=h))
    assert call['status']=='pending' and call['customer_message']
    raw_call=store.get('staff_calls',call['id']); raw_call.update(copy.deepcopy(UNKNOWN)); raw_call['token']=s['token']; store.put('staff_calls',raw_call)
    for status, action in [('accepted','accept'),('completed','complete')]:
        employee = client.post(f"/api/staff/calls/{call['id']}/{action}",auth=STAFF)
        assert employee.status_code==200 and s['token'] not in employee.text
        polled=safe(client.get(path, headers=h));assert polled['staff_calls'][0]['status']==status
    ended=safe(client.post(path+'/end',headers=h));assert ended['status']=='ended'
    assert safe(client.get(path,headers=h))['status']=='ended'


def test_tokens_scope_and_employee_audit_are_distinct(system):
    client, store, tools = system;s,h=create(client);other,oh=create(client);path=f"/api/sessions/{s['id']}"
    for wrong in [{}, {'X-Session-Token':'TEST-wrong'}, oh]:
        for method, suffix, body in [('GET','',None),('POST','/property',{'property_id':'No.15'}),('POST','/messages',{'text':'TEST'}),
                                     ('POST','/mortgage',{'loan_amount':30000000,'years':35,'rate_id':'TEST-mufg'}),
                                     ('POST','/staff-calls',{'reason':'TEST'}),('POST','/end',None),('POST','/realtime/greet',None)]:
            assert client.request(method,path+suffix,headers=wrong,json=body).status_code==403
        assert client.post(path+'/realtime',headers={**wrong,'Content-Type':'application/sdp'},content='v=0\r\nTEST').status_code==403
    safe(client.post(path+'/messages',json={'text':'住宅購入は？'},headers=h))
    assert client.post(path+'/property',json={'property_id':'TEST_UNPUBLISHED_PROPERTY'},headers=h).status_code==404
    assert client.post(path+'/mortgage',json={'years':35,'rate_id':'TEST-mufg'},headers=h).status_code==409
    explicit=safe(client.post(path+'/mortgage',json={'loan_amount':30000000,'years':35,'rate_id':'TEST-mufg'},headers=h))
    assert explicit['monthly_payment']==87439 and explicit['property_price'] is None
    for endpoint in ['/api/admin/sessions','/api/admin/documents','/api/admin/versions','/api/staff/calls']:
        assert client.get(endpoint).status_code==401
    assert client.get('/api/admin/sessions',auth=STAFF).status_code==401
    audit=client.get('/api/admin/sessions',auth=ADMIN).json();own=next(v for v in audit if v['id']==s['id'])
    assert own['snapshot']['property']['internal_note']==MARKER and own['tool_events'][0]['arguments']['internal_note']==MARKER
    assert s['token'] not in json.dumps(audit) and other['token'] not in json.dumps(audit)


def test_expiry_no_other_endpoint_bypass_and_history_is_not_current(system, monkeypatch):
    client, store, tools=system;s,h=create(client,property_id='No.15');path=f"/api/sessions/{s['id']}"
    safe(client.post(path+'/messages',json={'text':'No.15の設備'},headers=h))
    safe(client.post(path+'/mortgage',json={'years':35,'rate_id':'TEST-mufg'},headers=h))
    # Freeze projection and business clocks past source validity. Don't mutate a version.
    for module in ['app.services.customer_view','app.services.context','app.services.tools','app.models.domain']:
        monkeypatch.setattr(module+'.now', lambda:'2100-01-01T12:00:00+09:00')
    polled=safe(client.get(path,headers=h))
    assert polled['property'] is None and polled['products']==[] and polled['display_events']==[]
    assert polled['messages'] and all(m['historical'] for m in polled['messages'])
    assert client.get('/api/property').status_code==410
    assert client.post(path+'/property',json={'property_id':'No.15'},headers=h).status_code==409
    assert client.post(path+'/mortgage',json={'years':35,'rate_id':'TEST-mufg'},headers=h).status_code==409
    new,nh=create(client);assert new['property'] is None and new['products']==[]
    listing=safe(client.post(f"/api/sessions/{new['id']}/messages",json={'text':'紹介'},headers=nh))
    assert listing['display_events'][0]['properties']==[]
    assert safe(client.post(path+'/end',headers=h))['status']=='ended'


def test_public_sources_never_trust_filenames_locations_or_arbitrary_urls(system):
    client,store,tools=system
    for url in ['https://example.com/secret', 'http://127.0.0.1:8000/private', 'javascript:alert(1)',
                'https://www.mlit.go.jp/private', 'https://www.mlit.go.jp/totikensangyo/const/1_6_bf_000013.html?secret=TEST',
                'https://user:password@www.mlit.go.jp/totikensangyo/const/1_6_bf_000013.html']:
        raw=snapshot();raw['references'][0]['source_url']=url
        raw['property']['source_url']=url
        raw=approve_fixture(store,raw)
        with store.connect() as db:db.execute('INSERT INTO versions(payload) VALUES (?)',(json.dumps(raw),))
        s,h=create(client,property_id='No.15')
        assert s['property']['references'][0]=={'label':'確認・公開済み物件資料','url':None}


def test_empty_publication_has_no_unconfirmed_data(system):
    client,store,_=system
    with store.connect() as db:db.execute('DELETE FROM versions')  # isolated fixture only
    s,h=create(client);assert s['version'] is None and s['property'] is None and s['products']==[]
    assert 'TEST_UNPUBLISHED_PROPERTY' not in json.dumps(s)
    assert client.get('/api/property').status_code==410


def test_current_displays_do_not_resend_past_queries_or_unpublished_hits(system):
    client,store,_=system;s,h=create(client,property_id='No.15');path=f"/api/sessions/{s['id']}"
    safe(client.post(path+'/mortgage',json={'loan_amount':30000000,'years':35,'rate_id':'TEST-mufg'},headers=h))
    safe(client.post(path+'/messages',json={'text':'住宅購入は？'},headers=h))
    polled=safe(client.get(path,headers=h))
    assert [e['kind'] for e in polled['display_events']]==['sources']
    # A forged/internal source record is not promoted to a current display.
    store.event(s['id'],'tool',{'name':'search_property_knowledge','arguments':{'query':'TEST'},
                              'result':{'items':[{'text':'TEST_UNPUBLISHED_HIT','scope':'property',
                                                 'reference':{'document_id':'TEST-unpublished'}}]}})
    polled=safe(client.get(path,headers=h))
    assert 'TEST_UNPUBLISHED_HIT' not in json.dumps(polled)


def test_greeting_http_response_has_explicit_boundary(system,monkeypatch):
    client,_,_=system;s,h=create(client,mode='voice')
    async def greet(id):return dict(UNKNOWN,status='greeting_requested')
    monkeypatch.setattr(app.state.realtime,'greet',greet)
    assert safe(client.post(f"/api/sessions/{s['id']}/realtime/greet",headers=h))=={'status':'greeting_requested'}


def test_realtime_sideband_business_results_are_projected_not_raw(system):
    client,store,tools=system;s,h=create(client,mode='voice',property_id='No.15')
    record=observe_customer(store,store.get('sessions',s['id']),'借入額は3000万円です。')
    store.event(s['id'],'message',{'role':'user','text':'三菱UFJ銀行でお願いします','channel':'voice'})
    calls=[('get_property_overview',{}),('list_properties',{}),
           ('search_consultation_knowledge',{'query':'住宅購入','scope':'general'}),
           ('get_mortgage_rates',{}),
           ('calculate_mortgage',{'loan_amount':30000000,'property_price':None,'down_payment':None,'years':35,'rate_id':'TEST-mufg'}),
           ('call_staff',{'reason':'TEST相談','last_customer_question':'TEST'})]
    events=[]
    for i,(name,args) in enumerate(calls):
        events.extend([{'type':'response.function_call_arguments.done','call_id':f'TEST-{i}','name':name,'arguments':json.dumps(args)},
                       {'type':'response.done','response':{'status':'completed'}}])
    sock=TestSocket(events);service=app.state.realtime
    # No provider connection or hangup request in this scripted socket test.
    async def hangup(id):return 200
    service.hangup=hangup
    asyncio.run(service.listen(connection(record,sock)))
    outputs=[json.loads(e['item']['output']) for e in sock.sent if e.get('item',{}).get('type')=='function_call_output']
    assert len(outputs)==6
    assert MARKER not in json.dumps(outputs)
    assert outputs[0]['property']['price']==76900000
    assert outputs[3]['rates'][0]['id']=='TEST-mufg'
    assert outputs[4]['mortgage']['monthly_payment']==87439
    assert outputs[5]['staff_call']['status']=='pending'
    assert 'session_id' not in outputs[5] and 'reason' not in outputs[5]
