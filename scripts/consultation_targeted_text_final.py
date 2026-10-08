"""One actual AI loan call after the Japanese declaration and prompt fixes."""
import sys,json
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.config import settings
out=ROOT/'evidence/consultation_positioning/targeted_text_final.json'
if out.exists(): raise RuntimeError('Evidence exists; no silent replay')
c=httpx.Client(base_url='http://127.0.0.1:8001/api',timeout=150);assert c.get('/health').json()['demo_mode']=='test'
r=c.post('/sessions',json={'mode':'text'});r.raise_for_status();s=r.json();h={'X-Session-Token':s['token']}
result={'session_id':s['id'],'version':s['version'],'initial_property':s['snapshot']['property'],'mode':'REAL_OPENAI_TEXT_TARGETED_ONE_LOAN_CALL','ai_retries':0,'physical_microphone':'NOT_VERIFIED','status':'RUNNING'}
try:
 q='物件はまだ決めていません。借入額は三千万円です。35年です。三菱UFJ銀行の変動金利でお願いします。月額の試算をお願いします。'
 r=c.post(f"/sessions/{s['id']}/messages",headers=h,json={'text':q});r.raise_for_status();a=r.json();state=c.get(f"/sessions/{s['id']}",headers=h).json()
 result['question']=q;result['answer']=a;result['tool_events']=state['tool_events']
 calc=[e['result'] for e in state['tool_events'] if e['name']=='calculate_mortgage'];assert len(calc)==1
 assert calc[0]['monthly_payment']==87439 and calc[0]['loan_amount']==30000000 and calc[0]['property_price'] is None and state['property_id'] is None
 result['checks']={'japanese_amount_actual_tool_calculation':'PASS','no_default_property_payload_or_price':'PASS'}
 r=c.post(f"/sessions/{s['id']}/messages",headers=h,json={'text':'御社の営業時間は何時ですか？'});r.raise_for_status();result['company_policy']=r.json()
 assert result['company_policy']['provider']=='backend_policy' and 'ご相談ください' in result['company_policy']['answer']
 r=c.post(f"/sessions/{s['id']}/messages",headers=h,json={'text':'駅から何分ですか？'});r.raise_for_status();result['ambiguous_policy']=r.json();assert 'どの物件' in r.json()['answer']
 result['status']='PASS'
finally:
 r=c.post(f"/sessions/{s['id']}/end",headers=h);result['end_status']=r.status_code;out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'status':result['status'],'checks':result.get('checks'),'answer':result.get('answer',{}).get('answer')},ensure_ascii=False))
