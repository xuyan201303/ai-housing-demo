"""R2 owned TEST DB, deterministic provider, loopback traffic only."""
import os
import sys
import socket
import json
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
sys.path.insert(0, str(ROOT/'backend/tests'))
OUT = ROOT/'evidence/customer_knowledge_boundary_r2'
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(DATABASE_URL='sqlite:///./evidence/customer_knowledge_boundary_r2/ui-verified.db',
    UPLOAD_DIR='./evidence/customer_knowledge_boundary_r2/ui-uploads', OPENAI_API_KEY='',
    ADMIN_PASSWORD='TEST-r2-admin', STAFF_PASSWORD='TEST-r2-staff',
    DEMO_MODE='test', FRONTEND_ORIGIN='http://localhost:5186')
from app.main import app
from knowledge_boundary_fixtures import seed_pending
from public_boundary_fixtures import TestProvider
assert app.state.store.path == OUT/'ui-verified.db'
seed_pending(app.state.store)
app.state.ai = TestProvider(app.state.store, app.state.tools)
names = [str(p.relative_to(ROOT)) for folder in ['backend/app','frontend/src'] for p in (ROOT/folder).rglob('*') if p.suffix in {'.py','.ts','.tsx'}]
names += ['frontend/vite.config.ts','scripts/knowledge_boundary_test_server.py','backend/tests/knowledge_boundary_fixtures.py','backend/tests/public_boundary_fixtures.py']
(OUT/'test_server_manifest.json').write_text(json.dumps({'database':str(app.state.store.path),
    'frontend_origin':'http://localhost:5186','backend':'127.0.0.1:8016',
    'provider':'TEST_DETERMINISTIC_NOT_REAL_AI','paid_api_calls':0,'outbound':'LOOPBACK_ONLY',
    'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}},indent=2))
original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
def guard(address):
    if isinstance(address,tuple) and address[0] not in {'127.0.0.1','::1','localhost'}:
        raise RuntimeError('R2 TEST prohibits non-loopback connections')
def connect(self,address):guard(address);return original_connect(self,address)
def connect_ex(self,address):guard(address);return original_connect_ex(self,address)
socket.socket.connect, socket.socket.connect_ex = connect, connect_ex
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8016,log_level='warning')
