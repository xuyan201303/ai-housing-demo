"""Phase 1 TEST transports, fake electronic tones and isolated DB only."""
import asyncio
import json
import socket
from types import SimpleNamespace
from xml.etree import ElementTree
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models.domain import AppError
from app.repositories.store import Store
from app.services.documents import DocumentService
from app.services.sessions import SessionService
from app.services.tools import ToolService
from app.services.realtime import RealtimeService
from app.services.tts import TtsService, MAX_TEXT
from app.services.voice_output import VoiceOutputProvider, VoiceMode
from app.services.azure_tts import AzureTtsAdapter, speech_ssml
from fake_tts import FakeTtsProvider
from knowledge_boundary_fixtures import seed_pending, confirm_materials
from test_realtime import TestSocket, connection


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs): raise AssertionError('Phase 1 TEST prohibits outbound network')
    monkeypatch.setattr(socket.socket, 'connect', denied)


@pytest.fixture
def system(tmp_path, monkeypatch):
    store = Store(tmp_path / 'phase1-test.db')
    documents = DocumentService(store, settings)
    seed_pending(store); confirm_materials(documents)
    tools = ToolService(store)
    config = SimpleNamespace(api_key='TEST_NO_NETWORK', realtime_model=settings.realtime_model,
        realtime_voice=settings.realtime_voice, voice_output_provider='azure_tts')
    rt = RealtimeService(store, tools, config)
    fake = FakeTtsProvider()
    rt.output = VoiceOutputProvider(VoiceMode.JAPANESE_TTS, fake)
    rt.tts = TtsService(store, rt.output)
    async def hangup(*args): return 200
    rt.hangup = hangup
    for name, value in [('store', store), ('documents', documents), ('sessions', SessionService(store)), ('tools', tools), ('realtime', rt)]:
        monkeypatch.setattr(app.state, name, value)
    with TestClient(app) as client:
        result = client.post('/api/sessions', json={'mode':'voice'}).json()
        session = store.get('sessions', result['id'])
        record = dict(session, voice_output={'provider':'azure_tts','epoch':0,'latest_event_id':None})
        store.put('sessions', record)
        yield client, store, record, rt, fake, {'X-Session-Token':result['token']}


def response_events(text, rid='resp_TEST'):
    return [{'type':'response.created','response':{'id':rid}},
            {'type':'response.output_text.delta','response_id':rid,'item_id':'msg_TEST','delta':text[:8]},
            {'type':'response.output_text.delta','response_id':rid,'item_id':'msg_TEST','delta':text[8:]},
            {'type':'response.output_text.done','response_id':rid,'item_id':'msg_TEST','text':text},
            {'type':'response.output_audio_transcript.done','transcript':'TEST_IGNORE_WRONG_AUDIO'},
            {'type':'response.done','response':{'id':rid,'status':'completed','output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':text}]}]}}]


def save(system, text='借入額は3,000万円、35年、参考金利は1.195%です。'):
    _, store, session, rt, _, _ = system
    asyncio.run(rt.listen(connection(session, TestSocket(response_events(text)), active=False)))
    return store.get('sessions', session['id'])['voice_output']['latest_event_id']


def test_actual_routes_event_bound_dedup_and_no_arbitrary_text(system):
    client, store, session, rt, fake, headers = system
    eid = save(system)
    base = f'/api/sessions/{session["id"]}'
    answer = client.get(base+'/voice-answer?response_id=resp_TEST', headers=headers).json()
    assert set(answer) == {'assistant_event_id','display_text'} and answer['assistant_event_id'] == eid
    assert client.get(base+'/voice-output', headers=headers).json() == {'provider':'azure_tts'}
    assert client.post(base+'/speech',json={'assistant_event_id':eid,'text':'ATTACK'},headers=headers).status_code == 422
    for _ in range(2):
        audio = client.post(base+'/speech',json={'assistant_event_id':eid},headers=headers)
        assert audio.status_code == 200 and audio.content.startswith(b'RIFF')
        assert audio.headers['x-audio-test-only'] == 'true'
    assert fake.calls == [answer['display_text']]
    events = store.events(session['id'])
    assert len([e for e in events if e.get('role') == 'assistant']) == 1
    usage = [e for e in events if e['kind'] == 'tts_usage']
    assert len(usage) == 1 and usage[0]['test_only'] and usage[0]['characters'] == len(fake.calls[0])
    assert 'text' not in usage[0]
    assert client.post(base+'/speech/cancel',headers=headers).status_code==200
    assert client.post(base+'/speech',json={'assistant_event_id':eid},headers=headers).status_code==200
    assert len(fake.calls)==1  # cancel cannot evict a completed answer and bypass dedup


def test_wrong_token_other_session_user_event_and_end_rejected(system):
    client, store, session, rt, fake, headers = system
    eid = save(system); base = f'/api/sessions/{session["id"]}'
    other = client.post('/api/sessions', json={'mode':'voice'}).json()
    for tail, method, body in [('/speech','post',{'assistant_event_id':eid}),('/speech/cancel','post',None),('/voice-answer?response_id=resp_TEST','get',None),('/voice-output','get',None)]:
        for token in ['WRONG',other['token']]:
            result = getattr(client,method)(base+tail,headers={'X-Session-Token':token},**({'json':body} if method == 'post' else {}))
            assert result.status_code == 403
    uid = store.event(session['id'],'message',{'role':'user','text':'TEST'})
    assert client.post(base+'/speech',json={'assistant_event_id':uid},headers=headers).status_code == 409
    assert client.post(base+'/end',headers=headers).status_code == 200
    assert client.post(base+'/speech',json={'assistant_event_id':eid},headers=headers).status_code == 409
    assert fake.calls == []


@pytest.mark.parametrize('change',['epoch','property','expired','revoked','oversize','wrong_role','new_text_turn'])
def test_current_conditions_are_revalidated(system, change):
    client, store, session, rt, fake, headers = system
    eid=save(system, 'あ'*(MAX_TEXT+1) if change=='oversize' else 'TEST回答')
    record=store.get('sessions',session['id'])
    if change=='epoch':record['voice_output']['epoch']+=1;store.put('sessions',record)
    elif change=='property':record['property_id']='No.15';store.put('sessions',record)
    elif change=='revoked':
        d=store.get('documents','A-general');d['usage']='internal';store.put('documents',d)
    elif change=='expired':
        # Time advances beyond frozen source validity, without modifying approval proofs.
        import app.services.knowledge_access as access
        from unittest.mock import patch
        with patch.object(access,'now',lambda:'2100-01-01T00:00:00+09:00'):
            with pytest.raises(AppError):rt.tts.answer(record,eid)
        return
    elif change=='wrong_role':
        with store.connect() as db:
            row=db.execute('SELECT payload FROM events WHERE id=?',(eid,)).fetchone();payload=json.loads(row[0]);payload['role']='user'
            db.execute('UPDATE events SET payload=? WHERE id=?',(json.dumps(payload),eid))
    elif change=='new_text_turn':store.event(session['id'],'message',{'role':'user','text':'TEST新的文字咨询'})
    result=client.post(f'/api/sessions/{session["id"]}/speech',json={'assistant_event_id':eid},headers=headers)
    assert result.status_code in {404,409,422} and not fake.calls


def test_concurrency_cancel_timeout_and_explicit_retry(system):
    _, store, session, rt, fake, _=system
    eid=save(system);fake.delay=0.2
    async def run():
        a=asyncio.create_task(rt.tts.render(session,eid));b=asyncio.create_task(rt.tts.render(session,eid))
        await asyncio.gather(a,b)
        assert len(fake.calls)==1
        rt.tts.cache.clear();fake.delay=5
        pending=asyncio.create_task(rt.tts.render(session,eid));await asyncio.sleep(.02)
        await rt.interrupt_output(session['id'])
        with pytest.raises(AppError) as err:await pending
        assert err.value.code=='TTS_CANCELLED' and fake.cancelled==1 and not rt.tts.jobs
        record=store.get('sessions',session['id']);conn=connection(record,TestSocket(response_events('TEST新しい回答','resp_NEW')),active=False)
        await rt.listen(conn);new_eid=store.get('sessions',session['id'])['voice_output']['latest_event_id']
        rt.tts.timeout=.01
        with pytest.raises(AppError) as err:await rt.tts.render(record,new_eid)
        assert err.value.code=='TTS_FAILED' and not rt.tts.cache
        fake.delay=0;await rt.tts.render(record,new_eid)
    asyncio.run(run())
    assert [e['status'] for e in store.events(session['id']) if e['kind']=='tts_usage']==['completed','cancelled','failed','completed']


def test_failed_and_interrupted_responses_never_become_speech(system):
    _,store,session,rt,fake,_=system
    events=response_events('TEST旧回答')
    events.insert(-1,{'type':'input_audio_buffer.speech_started'})
    events += [{'type':'response.done','response':{'id':'resp_failed','status':'failed','output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':'FAILED_NOT_SPOKEN'}]}]}}]
    asyncio.run(rt.listen(connection(session,TestSocket(events),active=False)))
    assert not [e for e in store.events(session['id']) if e.get('role')=='assistant']
    assert not fake.calls


def test_text_only_actual_session_and_every_response(system, monkeypatch):
    _,store,session,rt,fake,_=system
    payloads=[];original=httpx.AsyncClient;sock=TestSocket(stay_open=True)
    def handler(req):
        data=req.content.decode();start=data.index('{"type": "realtime"');payloads.append(json.loads(data[start:data.index('\r\n--',start)]))
        return httpx.Response(200,text='v=0\r\nTEST',headers={'Location':'/calls/rtc_TEST_PHASE1'})
    monkeypatch.setattr(httpx,'AsyncClient',lambda *a,**kw:original(*a,**kw,transport=httpx.MockTransport(handler)))
    async def open_socket(*args,**kwargs):return sock
    monkeypatch.setattr('app.services.realtime.websockets.connect',open_socket)
    async def run():
        await rt.connect(session,'v=0\r\nTEST');await rt.greet(session['id']);await rt.close(session['id'])
    asyncio.run(run())
    assert payloads[0]['output_modalities']==['text'] and 'output' not in payloads[0]['audio']
    assert payloads[0]['model']==settings.realtime_model
    responses=[e['response'] for e in sock.sent if e['type']=='response.create']
    assert responses and all(r['output_modalities']==['text'] for r in responses)
    assert sock.closed and not rt.connections and not rt.tts.jobs


def test_failure_is_explicit_no_fallback_and_keeps_subtitle(system):
    client,store,session,rt,fake,headers=system
    eid=save(system);fake.fail=True
    result=client.post(f'/api/sessions/{session["id"]}/speech',json={'assistant_event_id':eid},headers=headers)
    assert result.status_code==502 and result.json()['error']['code']=='TTS_FAILED'
    assert '日本語音声生成に失敗' in result.json()['error']['message']
    assert client.get(f'/api/sessions/{session["id"]}/voice-answer?response_id=resp_TEST',headers=headers).json()['display_text']==fake.calls[0]
    assert rt.output.mode==VoiceMode.JAPANESE_TTS and len(fake.calls)==1


def test_http_request_abort_cancels_synthesis_without_vad_event(system):
    _,store,session,rt,fake,headers=system
    eid=save(system);fake.delay=5
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://TEST_ONLY') as client:
            request=asyncio.create_task(client.post(f'/api/sessions/{session["id"]}/speech',json={'assistant_event_id':eid},headers=headers))
            for _ in range(50):
                if fake.calls:break
                await asyncio.sleep(.01)
            assert fake.calls
            request.cancel()
            with pytest.raises(asyncio.CancelledError):await request
            assert fake.cancelled==1 and not rt.tts.jobs and not rt.tts.cache
    asyncio.run(run())
    assert [e['status'] for e in store.events(session['id']) if e['kind']=='tts_usage']==['cancelled']


def test_loan_property_and_staff_use_identical_saved_text(system):
    _,store,session,rt,fake,_=system
    text='借入額は3000万円です。35年、TEST変動金利でお願いします。'
    events=[{'type':'conversation.item.input_audio_transcription.completed','transcript':text},
        {'type':'response.function_call_arguments.done','call_id':'TEST_calc','name':'calculate_mortgage','arguments':json.dumps({'loan_amount':30000000,'years':35,'rate_id':'A-rates:rate:0'})},
        {'type':'response.done','response':{'status':'completed'}}]
    events+=response_events('借入額3,000万円、35年、年1.195%、月額87,439円です。審査を保証するものではありません。')
    async def run():
        await rt.listen(connection(session,TestSocket(events),active=False))
        record=store.get('sessions',session['id']);await rt.tts.render(record,record['voice_output']['latest_event_id'])
        q='この年収ならローン審査に絶対通りますか？'
        ev=[{'type':'input_audio_buffer.speech_started'},{'type':'conversation.item.input_audio_transcription.completed','transcript':q}]
        ev+=response_events('審査に必ず通るとはご案内できません。スタッフに確認を依頼しました。','resp_staff')
        await rt.listen(connection(record,TestSocket(ev),active=False))
        record=store.get('sessions',session['id']);await rt.tts.render(record,record['voice_output']['latest_event_id'])
    asyncio.run(run())
    answers=[e['text'] for e in store.events(session['id']) if e.get('role')=='assistant']
    assert fake.calls==answers and '87,439' in answers[0]
    loan=next(e['result'] for e in store.events(session['id']) if e.get('name')=='calculate_mortgage')
    assert loan['monthly_payment']==87439 and store.list('staff_calls')[0]['status']=='pending'


def test_azure_pronunciation_escaped_and_missing_configuration_no_call():
    text='三菱UFJ銀行、3,000万円、35年、1.195%、No.15。<script>&'
    xml=ElementTree.fromstring(speech_ssml(text,'ja-JP-NanamiNeural','customerservice'))
    assert ''.join(xml.itertext())==text
    aliases=[i.attrib['alias'] for i in xml.iter() if i.tag.endswith('sub')]
    assert aliases==['みつびしユーエフジェーぎんこう','1点1・9・5パーセント','15号地']
    with pytest.raises(AppError) as err:asyncio.run(AzureTtsAdapter(SimpleNamespace()).synthesize(text))
    assert err.value.code=='AZURE_NOT_CONFIGURED'


def test_azure_mock_list_style_and_audio_not_retry(monkeypatch):
    cfg=SimpleNamespace(azure_speech_key='TEST_ONLY',azure_speech_region='japaneast',azure_speech_voice='ja-JP-NanamiNeural',azure_speech_style='customerservice')
    calls=[];original=httpx.AsyncClient
    def handler(req):
        calls.append(req)
        if req.method=='GET':return httpx.Response(200,json=[{'ShortName':cfg.azure_speech_voice,'Locale':'ja-JP','StyleList':['customerservice']}])
        return httpx.Response(200,content=b'RIFF_TEST_AUDIO')
    monkeypatch.setattr(httpx,'AsyncClient',lambda *a,**kw:original(*a,**kw,transport=httpx.MockTransport(handler)))
    adapter=AzureTtsAdapter(cfg);asyncio.run(adapter.synthesize('3,000万円、35年'))
    assert len(calls)==2 and b'customerservice' in calls[1].content
    adapter.voice='ja-JP-ShioriNeural'
    with pytest.raises(AppError):asyncio.run(adapter.synthesize('TEST unavailable'))
    assert len(calls)==2


def test_audition_default_plan_has_zero_network_and_no_db():
    from scripts.azure_voice_audition import execute
    args=SimpleNamespace(voices=['ja-JP-NanamiNeural','ja-JP-ShioriNeural'],execute_paid=False)
    asyncio.run(execute(args))
