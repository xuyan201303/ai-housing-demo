"""R1 HTTP/UI isolation harness. TEST provider only, outbound sockets restricted."""
import os
import sys
import socket
import json
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
sys.path.insert(0,str(ROOT/'backend/tests'))
# Fixed dedicated fixture path; never the normal or previous acceptance database.
os.environ.update(DATABASE_URL='sqlite:///./evidence/public_response_boundary_r1/ui-test.db',
                  UPLOAD_DIR='./evidence/public_response_boundary_r1/ui-uploads',
                  OPENAI_API_KEY='', ADMIN_PASSWORD='TEST-r1-admin', STAFF_PASSWORD='TEST-r1-staff',
                  DEMO_MODE='test', FRONTEND_ORIGIN='http://localhost:5184')
from app.main import app
from app.services.tools import ToolService
from public_boundary_fixtures import seed, TestProvider, PoisonTools
assert app.state.store.path==ROOT/'evidence/public_response_boundary_r1/ui-test.db'
seed(app.state.store)
(ROOT/'evidence/public_response_boundary_r1/test_server_manifest.json').write_text(json.dumps({
    'database': str(app.state.store.path), 'provider': 'TEST_DETERMINISTIC_NOT_REAL_AI',
    'outbound_connections': 'LOOPBACK_ONLY', 'source_hashes': {
        name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in [
            'backend/app/schemas/customer.py', 'backend/app/services/customer_view.py',
            'backend/app/api/routes.py', 'backend/app/services/sessions.py', 'backend/app/services/realtime.py']
    }},indent=2))
app.state.tools=PoisonTools(ToolService(app.state.store))
app.state.ai=TestProvider(app.state.store,app.state.tools)
original_connect=socket.socket.connect
original_connect_ex=socket.socket.connect_ex
def guarded(address):
    if isinstance(address,tuple) and address[0] not in {'127.0.0.1','::1','localhost'}:
        raise RuntimeError('TEST harness forbids outbound connections')
def connect(self,address):guarded(address);return original_connect(self,address)
def connect_ex(self,address):guarded(address);return original_connect_ex(self,address)
socket.socket.connect=connect
socket.socket.connect_ex=connect_ex
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8014,log_level='warning')
