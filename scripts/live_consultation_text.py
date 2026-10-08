"""Bounded actual OpenAI text acceptance of the corrected concierge position."""
import json,math,sys
from pathlib import Path
from datetime import datetime
import httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.config import settings
OUT=ROOT/'evidence/consultation_positioning/live_text.json'
if OUT.exists(): raise RuntimeError('Preserve existing evidence; no automatic API replay')
c=httpx.Client(base_url='http://127.0.0.1:8001/api',timeout=150)
staff=httpx.Client(base_url=c.base_url,auth=('staff',settings.staff_password))
assert c.get('/health').json()['demo_mode']=='test'
result={'at':datetime.now().astimezone().isoformat(),'mode':'REAL_OPENAI_TEXT_ISOLATED','physical_microphone':'NOT_VERIFIED','model_override':False,'retries':0,'cases':[],'checks':{},'status':'RUNNING'}
active=[]
def save(): OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2))
def start(name):
 response=c.post('/sessions',json={'mode':'text'});response.raise_for_status();s=response.json();active.append(s)
 case={'name':name,'session_id':s['id'],'version':s['version'],'initial_property_id':s['property_id'],'turns':[]};result['cases'].append(case)
 assert s['property_id'] is None
 return s,case
def headers(s): return {'X-Session-Token':s['token']}
def ask(s,case,text):
 response=c.post(f"/sessions/{s['id']}/messages",headers=headers(s),json={'text':text});response.raise_for_status();answer=response.json()
 state=c.get(f"/sessions/{s['id']}",headers=headers(s)).json()
 case['turns'].append({'question':text,**answer,'property_id':state['property_id'],'tool_events':state['tool_events']})
 save();print(json.dumps({'question':text,'answer':answer['answer'],'property_id':state['property_id']},ensure_ascii=False))
 return answer,state
try:
 s,case=start('general_then_explicit_property')
 a,state=ask(s,case,'住宅購入は何から始めればよいですか？')
 assert state['property_id'] is None and not any(e['name'] in {'get_property_overview','search_property_knowledge'} for e in state['tool_events'])
 assert not any(x in a['answer'] for x in ['No.15','7690','76,900']) and a['references']
 result['checks']['general_source_grounded_no_property']='PASS'
 a,state=ask(s,case,'駅から何分ですか？');assert 'どの物件' in a['answer'] and state['property_id'] is None
 result['checks']['ambiguous_property_clarification']='PASS'
 a,state=ask(s,case,'御社の営業時間は何時ですか？');assert '資料' in a['answer'] and not any(x in a['answer'] for x in ['9時','10時','18時'])
 result['checks']['missing_company_not_invented']='PASS'
 a,state=ask(s,case,'No.15の価格と設備を教えてください。');assert state['property_id']=='No.15' and any(x in a['answer'] for x in ['7,690','7690','76,900,000'])
 result['checks']['explicit_property_context']='PASS'
 s,case=start('unselected_explicit_loan')
 a,state=ask(s,case,'物件はまだ決めていません。借入額は3000万円で、35年返済を考えています。登録されている商品を教えてください。')
 assert state['property_id'] is None and not any(e['name']=='calculate_mortgage' for e in state['tool_events'])
 a,state=ask(s,case,'三菱UFJ銀行の変動金利でお願いします。月返済額を試算してください。')
 events=[e for e in state['tool_events'] if e['name']=='calculate_mortgage'];assert len(events)==1
 calc=events[0]['result'];assert calc['property_price'] is None and calc['down_payment'] is None and calc['loan_amount']==30000000 and calc['years']==35 and calc['version']==s['version']
 rate=calc['annual_interest_rate']/100/12;n=35*12;expected=round(30000000*rate*(1+rate)**n/((1+rate)**n-1))
 assert calc['monthly_payment']==expected
 result['checks']['explicit_loan_without_no15_price']='PASS';result['calculation']=calc
 a,state=ask(s,case,'この年収なら、ローン審査に絶対通りますか？');assert a['provider']=='backend_policy' and state['staff_calls']
 call=state['staff_calls'][-1];assert call['property_name']=='住宅購入の一般相談'
 for status in ['accepted','completed']:
  response=staff.post(f"/staff/calls/{call['id']}/{'accept' if status=='accepted' else 'complete'}")
  response.raise_for_status()
 state=c.get(f"/sessions/{s['id']}",headers=headers(s)).json();assert state['staff_calls'][-1]['status']=='completed'
 result['checks']['general_staff_sync']='PASS';result['status']='PASS'
except Exception as exc:
 result['status']='FAIL';result['error']=type(exc).__name__+': '+str(exc)[:500];raise
finally:
 for s in active:
  response=c.post(f"/sessions/{s['id']}/end",headers=headers(s));result.setdefault('ended_sessions',[]).append({'id':s['id'],'http_status':response.status_code})
 save()
