import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config import settings
from app.models.domain import AppError
from app.repositories.store import Store
from app.services.documents import DocumentService
from app.services.sessions import SessionService
from app.services.tools import ToolService
from app.services.ai import AiService
from app.services.realtime import RealtimeService
from app.api.routes import router


@asynccontextmanager
async def lifespan(app):
    app.state.store.init()
    yield
    await app.state.realtime.close_all()


app = FastAPI(title='SANZO 住宅 AI接客 Demo', lifespan=lifespan, docs_url=None, redoc_url=None)
app.state.store = Store(settings.database)
app.state.documents = DocumentService(app.state.store, settings)
app.state.sessions = SessionService(app.state.store)
app.state.tools = ToolService(app.state.store)
app.state.ai = AiService(app.state.store, app.state.tools, settings)
app.state.realtime = RealtimeService(app.state.store, app.state.tools, settings)
app.state.parse_lock = asyncio.Lock()
app.add_middleware(CORSMiddleware, allow_origins=list({settings.frontend_origin, 'http://localhost:5173', 'http://127.0.0.1:5173'}), allow_methods=['GET','POST'], allow_headers=['Authorization','Content-Type','X-Session-Token'])


@app.middleware('http')
async def upload_limit(request: Request, call_next):
    value = request.headers.get('content-length')
    if value and (not value.isdigit() or int(value) > settings.max_upload_bytes + 65536):
        return JSONResponse(status_code=413, content={'error': {'code': 'REQUEST_SIZE', 'message': 'アップロードサイズ上限を超えています。'}})
    return await call_next(request)


class BodyLimit:
    """Count body bytes before multipart buffering, including chunked requests."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('method') != 'POST':
            return await self.app(scope, receive, send)
        total = 0
        chunks = []
        while True:
            message = await receive()
            total += len(message.get('body', b''))
            if total > settings.max_upload_bytes + 65536:
                # Reject outside the multipart parser: it would otherwise wrap a
                # receive exception into an unrelated 400 parsing error.
                response = JSONResponse(status_code=413, content={'error': {'code': 'REQUEST_SIZE', 'message': 'アップロードサイズ上限を超えています。'}})
                return await response(scope, receive, send)
            chunks.append(message)
            if message['type'] == 'http.disconnect' or not message.get('more_body', False):
                break
        index = 0
        async def buffered_receive():
            nonlocal index
            if index < len(chunks):
                message = chunks[index]; index += 1
                return message
            return await receive()
        await self.app(scope, buffered_receive, send)


app.add_middleware(BodyLimit)


@app.exception_handler(AppError)
async def error(request, exc):
    detail = {'code': exc.code, 'message': exc.message}
    if exc.field_errors:
        detail['field_errors'] = exc.field_errors
    return JSONResponse(status_code=exc.status, content={'error': detail})


@app.exception_handler(RequestValidationError)
async def validation(request, exc):
    detail = {'code': 'INVALID_INPUT', 'message': '入力内容を確認してください。'}
    if request.url.path.startswith('/api/admin/documents/'):
        fields = {}
        for item in exc.errors():
            path = [str(part) for part in item['loc'] if part != 'body']
            if path and path[0] == 'reviewed':
                path = path[1:]
            field = '.'.join(path)
            if field:
                fields[field] = '対応していない項目です。' if item['type'] == 'extra_forbidden' else '入力内容を確認してください。'
        if fields:
            detail['field_errors'] = fields
    return JSONResponse(status_code=422, content={'error': detail})


@app.exception_handler(Exception)
async def internal(request, exc):
    # The browser never receives paths, SDK exception text or credentials.
    return JSONResponse(status_code=500, content={'error': {'code': 'INTERNAL_ERROR', 'message': '処理に失敗しました。管理者へお知らせください。'}})


app.include_router(router)
