"""Read current runtime; write only evidence, never confirmation or publication."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime
import httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.config import settings
result={'checked_at':datetime.now().astimezone().isoformat(),'environments':{},'sdk_core_modified':False,'env_overwritten':False}
for name,port,front in [('normal',8000,5173),('isolated',8001,5174)]:
 c=httpx.Client(base_url=f'http://127.0.0.1:{port}/api',auth=('admin',settings.admin_password),timeout=30)
 health=c.get('/health');health.raise_for_status();docs=c.get('/admin/documents');docs.raise_for_status();v=c.get('/admin/versions');v.raise_for_status();sessions=c.get('/admin/sessions');sessions.raise_for_status()
 records=docs.json();versions=v.json();entry={'url':f'http://localhost:{front}/','backend':f'127.0.0.1:{port}','health':health.json(),'database':'data/housing.db' if name=='normal' else 'evidence/http-test.db','document_count':len(records),'parsed_count':sum(r['status']=='parsed' for r in records),'confirmed_count':sum(r['status'] in {'confirmed','published'} for r in records),'published_version':versions[0]['version'] if versions else None,'active_session_records':sum(s['status']=='active' for s in sessions.json()),'documents':[{'filename':r['filename'],'id':r['id'],'status':r['status'],'sha256':r['sha256']} for r in records]}
 if name=='normal':
  assert entry['document_count']==6 and entry['parsed_count']==6 and entry['confirmed_count']==0 and entry['published_version'] is None
  assert entry['active_session_records']==0
  assert all(hashlib.sha256((ROOT/'demo_documents'/r['filename']).read_bytes()).hexdigest()==r['sha256'] for r in records)
  entry['file_hash_reuse_verified']=True
 result['environments'][name]=entry
 result['environments'][name]['frontend_http_status']=httpx.get(f'http://localhost:{front}/').status_code
assert result['environments']['isolated']['published_version']==4
(ROOT/'evidence/consultation_positioning/final_readback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({name:{k:e[k] for k in ['document_count','parsed_count','confirmed_count','published_version','frontend_http_status']} for name,e in result['environments'].items()},ensure_ascii=False))
