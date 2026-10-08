"""Phase 1 isolated TEST harness. Fake Realtime transport + clearly fake beep.

No microphone, no paid API, no normal DB. TEST endpoints exist only in this script.
"""
import asyncio
import hashlib
import json
import os
import socket
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend/tests'))
OUT = ROOT / 'evidence/japanese_voice_architecture_phase1'
os.environ.update(DATABASE_URL='sqlite:///./evidence/japanese_voice_architecture_phase1/ui-test.db',
    UPLOAD_DIR='./evidence/japanese_voice_architecture_phase1/ui-uploads', OPENAI_API_KEY='',
    AZURE_SPEECH_KEY='', AZURE_SPEECH_REGION='', AZURE_SPEECH_VOICE='', VOICE_OUTPUT_PROVIDER='azure_tts',
    ADMIN_PASSWORD='TEST-phase1-admin', STAFF_PASSWORD='TEST-phase1-staff', DEMO_MODE='test',
    FRONTEND_ORIGIN='http://localhost:5188')
from fastapi import Header
from pydantic import BaseModel, ConfigDict
import httpx
import app.services.realtime as rt_module
from app.config import settings
from app.main import app
from app.services.voice_output import VoiceOutputProvider, VoiceMode
from app.services.tts import TtsService
from fake_tts import FakeTtsProvider
from knowledge_boundary_fixtures import seed_pending, confirm_materials
from public_boundary_fixtures import TestProvider
from test_japanese_voice import response_events

assert app.state.store.path == OUT / 'ui-test.db'
seed_pending(app.state.store)
if not app.state.store.versions():confirm_materials(app.state.documents)  # Owned TEST fixtures only.
app.state.ai = TestProvider(app.state.store, app.state.tools)
fake = FakeTtsProvider(duration=2.5)
rt = app.state.realtime
settings.api_key = 'TEST_ONLY_TRANSPORT_NO_PAID_API'
rt.settings = type('TestConfig', (), {'api_key':'TEST_ONLY','realtime_model':rt.settings.realtime_model,'realtime_voice':rt.settings.realtime_voice})()
rt.output = VoiceOutputProvider(VoiceMode.JAPANESE_TTS, fake)
rt.tts = TtsService(app.state.store, rt.output)
payloads = []


class QueueSocket:
    def __init__(self):self.queue=asyncio.Queue();self.sent=[];self.closed=False
    def __aiter__(self):return self
    async def __anext__(self):
        if getattr(self, 'previous', False):self.queue.task_done()
        event=await self.queue.get();self.previous=True
        if event is None:raise StopAsyncIteration
        return json.dumps(event,ensure_ascii=False)
    async def send(self,raw):self.sent.append(json.loads(raw))
    async def close(self):self.closed=True;await self.queue.put(None)
    async def emit(self,event):
        await self.queue.put(event)
        await self.queue.join()


original_client = httpx.AsyncClient
def mocked_openai(request):
    assert request.url.host == 'api.openai.com'
    if request.url.path.endswith('/hangup'):return httpx.Response(200)
    body=request.content.decode();start=body.index('{"type": "realtime"')
    payloads.append(json.loads(body[start:body.index('\r\n--',start)]))
    return httpx.Response(200,text='v=0\r\nTEST_PEER_NO_PAID_API',headers={'Location':'/calls/rtc_TEST_PHASE1'})
rt_module.httpx.AsyncClient = lambda *a,**kw:original_client(*a,**kw,transport=httpx.MockTransport(mocked_openai))
async def open_socket(*args,**kwargs):return QueueSocket()
rt_module.websockets.connect=open_socket


class TestTurn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text:str


@app.post('/api/TEST/voice-turn/{sid}')
async def turn(sid:str,body:TestTurn,x_session_token:str=Header(default='')):
    session=app.state.sessions.authorized(sid,x_session_token)
    conn=rt.connections[sid];ws=conn['socket'];rid='resp_TEST_'+str(len(app.state.store.events(sid)))
    events=[{'type':'input_audio_buffer.speech_started'},{'type':'input_audio_buffer.speech_stopped'},
        {'type':'conversation.item.input_audio_transcription.completed','transcript':body.text}]
    for event in events:await ws.emit(event)
    if '審査' in body.text:
        answer='TEST: 審査に必ず通るとはご案内できません。スタッフに確認を依頼しました。'
    else:
        if '紹介' in body.text:name,args='list_properties',{}
        elif 'No.15' in body.text:name,args='get_property_overview',{}
        elif '借入' in body.text:name,args='calculate_mortgage',{'loan_amount':30000000,'years':35,'rate_id':'A-rates:rate:0'}
        else:name,args='search_consultation_knowledge',{'scope':'general','query':'住宅購入'}
        await ws.emit({'type':'response.function_call_arguments.done','call_id':rid+'_tool','name':name,'arguments':json.dumps(args)})
        await ws.emit({'type':'response.done','response':{'id':rid+'_tool_response','status':'completed','output':[{'type':'function_call'}]}})
        raw=json.loads(next(e['item']['output'] for e in reversed(ws.sent) if e.get('item',{}).get('type')=='function_call_output'))
        if name=='calculate_mortgage':
            amount=raw['mortgage']['monthly_payment'];answer=f'TEST: 借入額3,000万円、35年、参考金利1.195%、月額{amount:,}円です。審査を保証するものではありません。'
        elif name=='list_properties':answer='TEST: 公開済みのサンプル No.15 をご案内できます。ご覧になりますか。'
        elif name=='get_property_overview':answer='TEST: No.15の価格は7,690万円です。TEST設備が掲載されています。'
        else:answer='TEST: 住宅購入は希望と予算を整理し、確認済みの資料を見て進めます。'
    final=response_events(answer,rid)
    for event in final:await ws.emit(event)
    # Failure/slow settings affect only FakeTtsProvider, never a real adapter.
    fake.fail='失敗' in body.text;fake.delay=3 if '遅い' in body.text else 0
    return {'events':events+final, 'provider':'TEST_ONLY', 'answer':answer}


@app.get('/api/TEST/voice-evidence')
def evidence():
    result={'paid_api_calls':0,'provider':'TEST_ONLY','fake_tts_inputs':fake.calls,'fake_cancelled':fake.cancelled,
        'realtime_session_configs':payloads,
        'usage':[e for s in app.state.store.list('sessions') for e in app.state.store.events(s['id']) if e['kind']=='tts_usage'],
        'connections':len(rt.connections),'tts_jobs':len(rt.tts.jobs),'tts_cache':len(rt.tts.cache)}
    (OUT/'test_transport_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result


original_connect, original_connect_ex=socket.socket.connect,socket.socket.connect_ex
def guard(address):
    if isinstance(address,tuple) and address[0] not in {'127.0.0.1','::1','localhost'}:
        raise RuntimeError('Phase 1 TEST permits loopback only')
def connect(self,address):guard(address);return original_connect(self,address)
def connect_ex(self,address):guard(address);return original_connect_ex(self,address)
socket.socket.connect,socket.socket.connect_ex=connect,connect_ex

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8018,log_level='warning')
