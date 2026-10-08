"""One bounded publication check using current real application code.

The authorization counter is durable outside the output directory.
No prompt/model changes or TEST answers are injected.

Run against a separately prepared TEST-only database; never seed normal data.
The existing Admin, Session, R1/R2, Tools and AiService handle all operations.
Only instrumentation below counts/logs real Responses calls and stops on errors.
"""
import asyncio
import copy
import fcntl
import hashlib
import json
import os
import re
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['PUBLICATION_CHECK_OUT']).resolve()
BUDGET = ROOT / 'evidence/phase2_live_ai_publication_check_budget.json'
if not OUT.is_relative_to(ROOT / 'evidence') or not (OUT / 'live-test.db').is_file():
    raise RuntimeError('A separately prepared TEST database is required')
# Hold an OS process lock before reading the authorization counter. Parallel
# processes cannot each spend from an independently loaded zero-call state.
budget_lock_fd = os.open(BUDGET.with_suffix('.lock'), os.O_RDWR | os.O_CREAT, 0o600)
try:
    fcntl.flock(budget_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise RuntimeError('Another process already owns this authorization budget')
# Fixed, task-wide budget. OUT, Session or process changes never reset it.
if BUDGET.exists():
    previous = json.loads(BUDGET.read_text())
    if previous.get('output_directory') != str(OUT):
        raise RuntimeError('This authorization budget is already bound to another output directory')
    if previous.get('calls') or previous.get('questions') or previous.get('created_sessions'):
        raise RuntimeError('This check cannot restart after any session or question; paid budget is not reset')
    (OUT / 'preflight_zero_calls.json').write_text(json.dumps(previous, indent=2))
else:
    fd = os.open(BUDGET, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump({'output_directory': str(OUT), 'calls': [], 'questions': [], 'created_sessions': []}, stream)
credentials = json.loads((ROOT / 'evidence/phase2_admin_e2e/credentials.json').read_text())
os.environ.update(DATABASE_URL='sqlite:///' + str(OUT / 'live-test.db'),
                  UPLOAD_DIR=str(OUT / 'unused-upload-target'), DEMO_MODE='demo',
                  FRONTEND_ORIGIN='http://localhost:8005',
                  ADMIN_PASSWORD=credentials['admin'], STAFF_PASSWORD=credentials['staff'])
sys.path.insert(0, str(ROOT / 'backend'))

from app.main import app
from app.config import settings
from app.models.domain import AppError, now
from app.services.ai import AiService, INSTRUCTIONS
import app.services.ai as ai_module
import httpx as real_httpx
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

assert app.state.store.path == OUT / 'live-test.db'
if not settings.api_key:
    raise RuntimeError('OPENAI_API_KEY is not configured; no paid call made')

QUESTION = 'TEST案内の確認方法は？'
LOCK = threading.Lock()
state = {'task': 'HOUSING_PHASE2_LIVE_AI_PUBLICATION_CHECK', 'output_directory': str(OUT),
         'question_limit': 2, 'generation_limit': 4, 'per_turn_generation_limit': 2, 'questions': [], 'calls': [],
         'created_sessions': [], 'halted': False, 'halt_reason': None}
active_session = None


def write(name, value):
    path = OUT / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    os.chmod(path, 0o600)


def flush():
    # Persist the shared authorization counter before any outbound request.
    temporary = BUDGET.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    os.chmod(temporary, 0o600)
    temporary.replace(BUDGET)
    write('calls.json', state)


def halt(reason):
    state.update(halted=True, halt_reason=reason)
    flush()


class GuardedClient:
    def __init__(self, *args, **kwargs):
        kwargs.update(follow_redirects=False, transport=real_httpx.AsyncHTTPTransport(retries=0))
        self.client = real_httpx.AsyncClient(*args, **kwargs)

    async def __aenter__(self):
        await self.client.__aenter__()
        return self

    async def __aexit__(self, *args):
        return await self.client.__aexit__(*args)

    async def post(self, url, **kwargs):
        with LOCK:
            turn_calls = sum(c['session_id'] == active_session for c in state['calls'])
            if state['halted'] or len(state['calls']) >= 4 or turn_calls >= 2:
                if not state['halted']:
                    halt('PER_TURN_LIMIT_REACHED' if turn_calls >= 2 else 'GENERATION_LIMIT_REACHED')
                raise AppError('LIVE_CHECK_STOPPED', '今回の文字検証は停止しました。追加送信は行いません。', 409)
            body = copy.deepcopy(kwargs.get('json', {}))
            if url != 'https://api.openai.com/v1/responses' or body.get('model') != settings.text_model:
                halt('UNAUTHORIZED_PROVIDER_OR_MODEL')
                raise AppError('LIVE_CHECK_STOPPED', '検証範囲外の接続を停止しました。', 409)
            entry = {'number': len(state['calls']) + 1, 'session_id': active_session,
                     'turn_request_number': turn_calls + 1,
                     'counted_before_outbound_at': now(), 'status': 'COUNTED_BEFORE_SEND'}
            state['calls'].append(entry)
            write(f"request_{entry['number']}.json", body)  # Never includes auth headers.
            flush()  # Durable count before each actual outbound request.
        try:
            response = await self.client.post(url, **kwargs)
        except real_httpx.HTTPError:
            entry.update(status='CONNECTION_ERROR', finished_at=now())
            halt('CONNECTION_ERROR_NO_RETRY')
            raise
        entry.update(http_status=response.status_code, finished_at=now())
        try:
            data = response.json()
        except ValueError:
            entry.update(status='INVALID_RESPONSE_JSON')
            write(f"response_{entry['number']}.json", {'http_status': response.status_code,
                                                       'body': response.text})
            halt('INVALID_RESPONSE_JSON')
            raise AppError('LIVE_CHECK_STOPPED', '応答形式が不正なため検証を停止しました。', 502)
        write(f"response_{entry['number']}.json", data)
        entry['usage'] = data.get('usage')
        entry['response_id'] = data.get('id')
        entry['response_status'] = data.get('status')
        if response.is_error or data.get('error'):
            entry['status'] = 'API_ERROR'
            halt('API_ERROR_NO_RETRY')
            raise AppError('LIVE_CHECK_STOPPED', 'APIエラーのため検証を停止しました。追加送信は行いません。', 502)
        output = data.get('output', [])
        calls = [item for item in output if item.get('type') == 'function_call']
        text = '\n'.join(part.get('text', '') for item in output if item.get('type') == 'message'
                         for part in item.get('content', []) if part.get('type') == 'output_text')
        if data.get('status') != 'completed' or (not calls and not text):
            entry['status'] = 'INCOMPLETE_OR_EMPTY'
            halt('INCOMPLETE_OR_EMPTY_RESPONSE')
            raise AppError('LIVE_CHECK_STOPPED', '応答が完了していないため検証を停止しました。', 502)
        for call in calls:
            try:
                arguments = json.loads(call['arguments'])
            except (ValueError, KeyError):
                halt('INVALID_TOOL_ARGUMENTS')
                raise AppError('LIVE_CHECK_STOPPED', 'ツール入力が不正なため停止しました。', 502)
            if (call.get('name') not in {'get_consultation_context', 'search_consultation_knowledge'}
                    or arguments.get('scope', 'general') != 'general'):
                halt('OUT_OF_SCOPE_MODEL_TOOL_REQUEST')
                raise AppError('LIVE_CHECK_STOPPED', '今回のFAQ検証以外の要求を停止しました。', 409)
        entry['status'] = 'COMPLETED'
        flush()
        return response


# Module-local replacement only. All request bodies and response processing
# remain the current application AiService's; no TEST answers or prompt edits.
ai_module.httpx = SimpleNamespace(AsyncClient=GuardedClient, HTTPError=real_httpx.HTTPError)
original_execute = app.state.tools.execute


def audited_execute(session, name, arguments, *args, **kwargs):
    try:
        result = original_execute(session, name, arguments, *args, **kwargs)
    except Exception:
        if active_session:
            halt('BUSINESS_TOOL_ERROR')
        raise
    if active_session:
        path = OUT / 'tool_results.json'
        events = json.loads(path.read_text()) if path.exists() else []
        events.append({'at': now(), 'session_id': session['id'], 'name': name,
                       'arguments': arguments, 'result': result})
        write('tool_results.json', events)
        if isinstance(result, dict) and result.get('error'):
            halt('BUSINESS_TOOL_ERROR')
    return result


app.state.tools.execute = audited_execute


class BoundedAiService(AiService):
    async def respond(self, session, text):
        global active_session
        with LOCK:
            if (state['halted'] or active_session is not None
                    or len(state['questions']) >= 2 or len(state['calls']) >= 4
                    or text != QUESTION or session['id'] not in state['created_sessions']
                    or any(item['session_id'] == session['id'] for item in state['questions'])):
                raise AppError('LIVE_CHECK_STOPPED', '今回は指定のFAQを各接客で1回だけ検証します。追加送信は行いません。', 409)
            state['questions'].append({'session_id': session['id'], 'version': session['version'],
                                       'text': text, 'at': now()})
            active_session = session['id']
            flush()
        try:
            result = await super().respond(session, text)
            write(f"answer_{len(state['questions'])}.json", result)
            return result
        except Exception:
            if not state['halted']:
                halt('APPLICATION_OR_PROVIDER_FAILURE')
            raise
        finally:
            active_session = None


app.state.ai = BoundedAiService(app.state.store, app.state.tools, settings)
original_start = app.state.sessions.start


def bounded_start(mode='text', property_id=None):
    with LOCK:
        if mode != 'text' or property_id or len(state['created_sessions']) >= 2 or state['halted']:
            raise AppError('LIVE_CHECK_SCOPE', '今回の検証は文字接客2件だけです。', 409)
        result = original_start(mode, property_id)
        state['created_sessions'].append(result['id'])
        flush()
        return result


app.state.sessions.start = bounded_start


@app.middleware('http')
async def live_boundary(request, call_next):
    path = request.url.path
    if any(word in path for word in ('realtime', '/voice', '/speech', '/mortgage', '/staff-calls')):
        return JSONResponse(status_code=403, content={'error': {'code': 'LIVE_CHECK_SCOPE', 'message': '今回の検証は文字FAQだけです。'}})
    if request.method == 'POST' and (path == '/api/admin/documents' or path.endswith('/parse')):
        return JSONResponse(status_code=403, content={'error': {'code': 'LIVE_CHECK_SCOPE', 'message': '再取込・再解析は行いません。'}})
    response = await call_next(request)
    response.headers['X-SANZO-Live-Check'] = 'HOUSING_PHASE2_LIVE_AI_PUBLICATION_CHECK'
    return response


DIST = ROOT / 'frontend/dist'
app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='live-customer-assets')


@app.get('/')
@app.get('/admin')
@app.get('/staff')
def temporary_frontend():
    html = (DIST / 'index.html').read_text()
    notice = '<div style="padding:12px;background:#fff2d2;color:#553900;font:14px sans-serif">一時LIVE文字検証 / 自有TESTデータ / 実OpenAI。質問は指定FAQを2件、モデル生成は合計最大4回・1回の質問で最大2回。通常5177ではありません。音声・マイクは使用しません。</div>'
    # This temporary page hides only the voice-start button. Core compiled
    # Customer/Admin bundle remains untouched; server also blocks voice routes.
    return HTMLResponse(html.replace('<body>', '<body>' + notice + '<style>.start-area > button[title]{display:none}</style>'))


flush()
write('runtime.json', {'task': 'HOUSING_PHASE2_LIVE_AI_PUBLICATION_CHECK', 'at': now(),
                      'database': str(settings.database), 'url': 'http://localhost:8005',
                      'api_key_configured': bool(settings.api_key), 'model': settings.text_model,
                      'instructions_sha256': hashlib.sha256(INSTRUCTIONS.encode()).hexdigest(),
                      'normal_db_connected': False, 'provider': 'CURRENT_APPLICATION_REAL_AISERVICE',
                      'retries': 0, 'question_limit': 2, 'generation_limit': 4, 'per_turn_generation_limit': 2,
                      'budget_path': str(BUDGET), 'application_ai_class': AiService.__module__ + '.' + AiService.__name__,
                      'ai_service_sha256': hashlib.sha256((ROOT / 'backend/app/services/ai.py').read_bytes()).hexdigest(),
                      'ai_evidence_sha256': hashlib.sha256((ROOT / 'backend/app/services/ai_evidence.py').read_bytes()).hexdigest(),
                      'voices_called': False})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8005, log_level='warning')
