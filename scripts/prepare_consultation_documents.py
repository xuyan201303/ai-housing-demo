"""Upload/parse source FAQs normally; only explicitly isolated TEST may review/publish."""
import hashlib,json,sys
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.config import settings
FILES=['住宅購入基礎FAQ_demo.pdf','住宅ローン基礎FAQ_demo.pdf']
report={'normal':{},'isolated':{},'physical_microphone':'NOT_VERIFIED'}
for label,port in [('normal',8000),('isolated',8001)]:
 c=httpx.Client(base_url=f'http://127.0.0.1:{port}/api',auth=('admin',settings.admin_password),timeout=120)
 health=c.get('/health');health.raise_for_status()
 assert health.json()['demo_mode']==('demo' if label=='normal' else 'test')
 records=c.get('/admin/documents').json();prepared=[]
 for name in FILES:
  content=(ROOT/'demo_documents'/name).read_bytes();sha=hashlib.sha256(content).hexdigest()
  same=next((d for d in records if d['sha256']==sha and d['status'] in {'uploaded','parsed','confirmed','published'}),None)
  if same is None:
   response=c.post('/admin/documents',files={'file':(name,content,'application/pdf')});response.raise_for_status();same=response.json()
  if same['status']=='uploaded':
   response=c.post(f"/admin/documents/{same['id']}/parse");response.raise_for_status();record=response.json()
  else:
   response=c.get(f"/admin/documents/{same['id']}");response.raise_for_status();record=response.json()
  assert record['sdk_version']=='1.8.0' and record['normalized']['document']['scope']=='general' and record['normalized']['property']=={}
  if label=='isolated' and record['status']=='parsed':
   response=c.post(f"/admin/documents/{record['id']}/confirm",json={'reviewed':record['normalized'],'note':'TEST-only isolated source scope verification. Not human approval for normal Demo.'});response.raise_for_status();record=response.json()
  prepared.append({'id':record['id'],'filename':record['filename'],'sha256':sha,'status':record['status'],'sdk_version':record['sdk_version'],'sdk_api':record['sdk_api'],'metadata':record['normalized']['document'],'knowledge_pages':len(record['normalized']['knowledge'])})
 if label=='isolated':
  versions=c.get('/admin/versions').json();latest=versions[0];ids=list(dict.fromkeys(latest['document_ids']+[r['id'] for r in prepared]))
  if ids!=latest['document_ids']:
   response=c.post('/admin/publish',json={'document_ids':ids});response.raise_for_status();latest=response.json()
  version=latest['version']
 else:
  versions=c.get('/admin/versions').json();version=versions[0]['version'] if versions else None
 current=c.get('/admin/documents').json()
 report[label]={'url':f'http://localhost:{5173 if label=="normal" else 5174}','database':'data/housing.db' if label=='normal' else 'evidence/http-test.db','health':health.json(),'documents':prepared,'registered_count':len(current),'confirmed_count':sum(d['status'] in {'confirmed','published'} for d in current),'published_version':version}
 print(json.dumps({'environment':label,'prepared':[(d['filename'],d['status'],d['knowledge_pages']) for d in prepared],'published_version':version},ensure_ascii=False))
(ROOT/'evidence/consultation_positioning/document_preparation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
