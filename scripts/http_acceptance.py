"""Real HTTP + SANZO SDK acceptance, in a separate explicit test instance.
Never seeds the normal Demo DB. Missing OpenAI key is a BLOCKED result.
"""
import json
import os
from pathlib import Path
import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ENV = dotenv_values(ROOT/'.env')
URL = os.getenv('ACCEPTANCE_URL', 'http://127.0.0.1:8001')


def main():
    client = httpx.Client(base_url=URL+'/api', timeout=60, auth=('admin',ENV['ADMIN_PASSWORD']))
    health = client.get('/health'); health.raise_for_status()
    assert health.json()['demo_mode'] == 'test', 'Refusing to mutate a non-test instance'
    assert client.get('/admin/documents',auth=('admin','invalid')).status_code == 401
    ids=[]
    for filename in ['物件概要_demo.pdf','設備仕様_demo.pdf','周辺環境_demo.pdf','住宅ローン_demo.xlsx']:
        file=ROOT/'demo_documents'/filename
        r=client.post('/admin/documents',files={'file':(filename,file.read_bytes())});r.raise_for_status();id=r.json()['id']
        assert client.post('/admin/publish',json={'document_ids':[id]}).status_code == 409
        r=client.post(f'/admin/documents/{id}/parse');r.raise_for_status(); parsed=r.json()
        r=client.post(f'/admin/documents/{id}/confirm',json={'reviewed':parsed['normalized'],'note':'TEST HTTP acceptance of self-generated source-grounded documents; not user manual approval'});r.raise_for_status()
        ids.append(id)
    r=client.post('/admin/publish',json={'document_ids':ids});r.raise_for_status(); snapshot=r.json()
    assert snapshot['property']['price'] == 76900000
    assert len(snapshot['property']['equipment'])==15
    assert len(snapshot['rates'])==2
    r=client.post('/sessions',json={'mode':'text'});r.raise_for_status();s=r.json(); headers={'X-Session-Token':s['token']}
    r=client.post(f"/sessions/{s['id']}/messages",headers=headers,json={'text':'駅から何分ですか？'})
    ai='BLOCKED: missing OPENAI_API_KEY' if r.status_code==503 else 'LIVE_RESPONSE_RECEIVED_NOT_SEMANTIC_ACCEPTANCE'
    if r.status_code==503:
        assert r.json()['error']['code']=='OPENAI_NOT_CONFIGURED'
    else:
        r.raise_for_status()
    out={'mode':'isolated_test_http','sdk':'PASS','upload_parse_confirm_publish':'PASS','source_references':'PASS','published_version':snapshot['version'],'document_ids':ids,'session_id':s['id'],'ai':ai,'voice':'NOT_VERIFIED'}
    try:
        rate=snapshot['rates'][1]
        r=client.post(f"/sessions/{s['id']}/mortgage",headers=headers,json={'down_payment':5000000,'years':35,'rate_id':rate['id']});r.raise_for_status();calc=r.json()
        assert calc['annual_interest_rate']==3.94
        out['mortgage']={'status':'PASS','result':calc}
        r=client.post(f"/sessions/{s['id']}/staff-calls",headers=headers,json={'reason':'住宅ローン審査について','last_customer_question':'年収500万円なら絶対ローン通りますか？'});r.raise_for_status();call=r.json()
        staff=httpx.Client(base_url=URL+'/api',auth=('staff',ENV['STAFF_PASSWORD']))
        assert any(c['id']==call['id'] for c in staff.get('/staff/calls').json())
        assert staff.post(f"/staff/calls/{call['id']}/accept").json()['status']=='accepted'
        assert client.get(f"/sessions/{s['id']}",headers=headers).json()['staff_calls'][0]['status']=='accepted'
        assert staff.post(f"/staff/calls/{call['id']}/complete").json()['status']=='completed'
        assert client.get(f"/sessions/{s['id']}",headers=headers).json()['staff_calls'][0]['status']=='completed'
        out['staff_notification']='PASS: persisted backend record, separate staff auth, customer readback accepted/completed'
    except httpx.HTTPStatusError as exc:
        out['phase3']='FAIL '+str(exc.response.status_code)
        raise
    finally:
        (ROOT/'evidence/http_acceptance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k not in {'mortgage','document_ids','session_id'}},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
