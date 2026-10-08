import asyncio
import hashlib
from app.services.ai import voice_instructions
import secrets
from fastapi import Form, APIRouter, Depends, Header, Request, UploadFile
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import Response
from app.config import settings
from app.models.domain import AppError
from app.schemas.domain import RevisionInput, PublicationDraftCreate, PublicationDraftInput, SessionStart, PropertySelection, MessageInput, ConfirmationInput, UsageInput, PublishInput, StaffInput, MortgageInput, DraftInput, DraftConfirmationInput
from app.schemas.customer import CustomerSession, CustomerSessionCreated, CustomerAnswer, CustomerMortgage, CustomerStaffCall, CustomerGreeting
from app.services.customer_view import session_view, answer_view, mortgage_view, staff_view
from app.services.context import snapshot_for
from app.services.sessions import employee_payload
from app.schemas.customer import CustomerVoiceAnswer, CustomerSpeechInput, CustomerVoiceOutput, CustomerSpeechCancelled

router = APIRouter(prefix='/api')
basic = HTTPBasic(auto_error=False)


def auth(credentials, allowed):
    if not credentials:
        raise AppError('AUTH_REQUIRED', 'ログインしてください。', 401)
    expected = {'admin': settings.admin_password, 'staff': settings.staff_password}
    valid = credentials.username in allowed and bool(expected.get(credentials.username))
    if not valid or not secrets.compare_digest(credentials.password, expected.get(credentials.username, '')):
        raise AppError('AUTH_FAILED', 'ユーザー名・パスワードを確認してください。', 401)


def admin(credentials: HTTPBasicCredentials | None = Depends(basic)):
    auth(credentials, {'admin'})
    return credentials.username


def staff(credentials: HTTPBasicCredentials | None = Depends(basic)):
    auth(credentials, {'admin', 'staff'})


@router.get('/health')
def health(request: Request):
    return {'status': 'ok', 'admin_publication_contract_version': 1 if request.app.state.store.publication_schema_ready() else 0, 'admin_publication_schema_ready': request.app.state.store.publication_schema_ready(), 'knowledge_boundary_version': 2, 'sdk_version': request.app.state.documents.adapter.sdk_version, 'demo_mode': settings.demo_mode, 'ai_configured': bool(settings.api_key), 'realtime_configured': bool(settings.api_key), 'realtime_voice': settings.realtime_voice, 'voice_instructions_sha256': hashlib.sha256(voice_instructions().encode()).hexdigest()}


@router.get('/property')
def property(request: Request):
    raise AppError('PROPERTY_ENDPOINT_REMOVED', '物件資料は接客を開始して、対象物件を選択してご覧ください。', 410)


@router.post('/admin/documents', dependencies=[Depends(admin)])
async def upload(request: Request, file: UploadFile, duplicate_action: str = Form(default='check'), replaces_document_id: str | None = Form(default=None), replaces_confirmation_id: int | None = Form(default=None), reuse_document_id: str | None = Form(default=None)):
    content = await file.read(settings.max_upload_bytes + 1)
    await file.close()
    return request.app.state.documents.upload(file.filename or 'upload', content, duplicate_action, replaces_document_id, replaces_confirmation_id, reuse_document_id)


@router.get('/admin/documents', dependencies=[Depends(admin)])
def documents(request: Request):
    return [request.app.state.documents.list_item(r) for r in request.app.state.store.list('documents')]


@router.get('/admin/documents/duplicates', dependencies=[Depends(admin)])
def duplicates(sha256: str, request: Request):
    return request.app.state.documents.duplicates(sha256)


@router.get('/admin/documents/{id}', dependencies=[Depends(admin)])
def document(id: str, request: Request):
    record = request.app.state.store.get('documents', id)
    return dict(record, approved_revisions=request.app.state.documents.revisions(id))


@router.get('/admin/documents/{id}/draft', dependencies=[Depends(admin)])
def draft(id: str, request: Request):
    return request.app.state.documents.get_draft(id)


@router.post('/admin/documents/{id}/draft')
def save_draft(id: str, body: DraftInput, request: Request, actor: str = Depends(admin)):
    return request.app.state.documents.save_draft(id, body.reviewed.model_dump(), body.note, body.usage,
                                                body.document_sha256, body.source_revision, body.revision, actor)


@router.post('/admin/documents/{id}/draft/confirm')
def confirm_draft(id: str, body: DraftConfirmationInput, request: Request, actor: str = Depends(admin)):
    return request.app.state.documents.confirm_draft(id, body.note, body.document_sha256,
                                                   body.source_revision, body.revision, actor)


@router.post('/admin/documents/{id}/parse', dependencies=[Depends(admin)])
async def parse(id: str, request: Request):
    async with request.app.state.parse_lock:
        return await asyncio.to_thread(request.app.state.documents.parse, id)


@router.post('/admin/documents/{id}/confirm')
def confirm(id: str, body: ConfirmationInput, request: Request, actor: str = Depends(admin)):
    return request.app.state.documents.confirm(id, body.reviewed.model_dump(), body.note, body.usage, actor)


@router.post('/admin/documents/{id}/usage')
def usage(id: str, body: UsageInput, request: Request, actor: str = Depends(admin)):
    return request.app.state.documents.set_usage(id, body.usage, body.note, actor)


def publication_service(request):
    from app.services.publications import PublicationService
    return PublicationService(request.app.state.store, request.app.state.documents)


@router.post('/admin/documents/{id}/revisions')
def begin_revision(id: str, body: RevisionInput, request: Request, actor: str = Depends(admin)):
    return request.app.state.documents.begin_revision(id, body.reason, actor)


@router.get('/admin/documents/{id}/revisions', dependencies=[Depends(admin)])
def revisions(id: str, request: Request):
    return request.app.state.documents.revisions(id)


@router.post('/admin/documents/{id}/updates/cancel')
def cancel_update(id: str, request: Request, actor: str = Depends(admin)):
    return request.app.state.documents.cancel_update(id, actor)


@router.get('/admin/publication-drafts', dependencies=[Depends(admin)])
def publication_drafts(request: Request):
    return publication_service(request).list()


@router.post('/admin/publication-drafts')
def create_publication_draft(body: PublicationDraftCreate, request: Request, actor: str = Depends(admin)):
    return publication_service(request).create(body.restore_version, actor)


@router.get('/admin/publication-drafts/{id}', dependencies=[Depends(admin)])
def publication_draft(id: str, request: Request):
    return publication_service(request).get(id)


@router.post('/admin/publication-drafts/{id}')
def save_publication_draft(id: str, body: PublicationDraftInput, request: Request, actor: str = Depends(admin)):
    return publication_service(request).save(id, body.revision, [i.model_dump(exclude_none=True) | {'confirmation_id': i.confirmation_id} for i in body.items], body.note, actor)


@router.post('/admin/publication-drafts/{id}/preview', dependencies=[Depends(admin)])
def preview_publication_draft(id: str, request: Request):
    return publication_service(request).preview(id)


@router.post('/admin/versions/{version}/restore-draft')
def restore_publication_draft(version: int, request: Request, actor: str = Depends(admin)):
    return publication_service(request).create(version, actor)


@router.post('/admin/publish')
def publish(body: PublishInput, request: Request, actor: str = Depends(admin)):
    if body.document_ids is not None or not all((body.draft_id, body.preview_token, body.idempotency_key)) or body.draft_revision is None:
        raise AppError('PUBLICATION_PREVIEW_REQUIRED', '公開草案を保存し、変更内容をプレビューしてから公開してください。', 409)
    return publication_service(request).publish(body.draft_id, body.draft_revision, body.preview_token, body.idempotency_key, actor)


@router.get('/admin/versions', dependencies=[Depends(admin)])
def versions(request: Request):
    return request.app.state.store.versions()


@router.get('/admin/sessions', dependencies=[Depends(admin)])
def histories(request: Request):
    return [request.app.state.sessions.employee_view(r) for r in request.app.state.store.list('sessions')]


@router.post('/sessions', response_model=CustomerSessionCreated)
def start(body: SessionStart, request: Request):
    record = request.app.state.sessions.start(body.mode, body.property_id)
    return session_view(request.app.state.store, record, created=True)


@router.post('/sessions/{id}/property', response_model=CustomerSession)
def select_property(id: str, body: PropertySelection, request: Request, x_session_token: str = Header(default='')):
    from app.services.context import bind
    record=request.app.state.sessions.authorized(id,x_session_token)
    return session_view(request.app.state.store, bind(request.app.state.store,record,body.property_id))


@router.get('/sessions/{id}', response_model=CustomerSession)
def session(id: str, request: Request, x_session_token: str = Header(default='')):
    record = request.app.state.sessions.authorized(id, x_session_token, active=False)
    return session_view(request.app.state.store, record)


@router.post('/sessions/{id}/end', response_model=CustomerSession)
async def end(id: str, request: Request, x_session_token: str = Header(default='')):
    record = request.app.state.sessions.authorized(id, x_session_token, allow_legacy=True)
    if hasattr(request.app.state, 'realtime'):
        await request.app.state.realtime.close(id)
    request.app.state.sessions.end(record)
    return session_view(request.app.state.store, request.app.state.store.get('sessions', id))


@router.post('/sessions/{id}/messages', response_model=CustomerAnswer)
async def message(id: str, body: MessageInput, request: Request, x_session_token: str = Header(default='')):
    record = request.app.state.sessions.authorized(id, x_session_token)
    raw = await request.app.state.ai.respond(record, body.text)
    return answer_view(request.app.state.store, record, raw)


@router.post('/sessions/{id}/staff-calls', response_model=CustomerStaffCall)
def call_staff(id: str, body: StaffInput, request: Request, x_session_token: str = Header(default='')):
    record = request.app.state.sessions.authorized(id, x_session_token)
    return staff_view(request.app.state.tools.execute(record, 'call_staff', body.model_dump()))


@router.post('/sessions/{id}/mortgage', response_model=CustomerMortgage)
def mortgage(id: str, body: MortgageInput, request: Request, x_session_token: str = Header(default='')):
    record = request.app.state.sessions.authorized(id, x_session_token)
    result = request.app.state.tools.execute(record, 'calculate_mortgage', body.model_dump())
    value = mortgage_view(result, snapshot_for(request.app.state.store, record))
    if value is None:
        raise AppError('MORTGAGE_RESULT_UNAVAILABLE', '現在有効な試算結果を確認できません。スタッフにご相談ください。', 409)
    return value


@router.get('/staff/calls', dependencies=[Depends(staff)])
def calls(request: Request):
    return employee_payload(request.app.state.store.list('staff_calls'))


@router.post('/staff/calls/{id}/accept', dependencies=[Depends(staff)])
def accept(id: str, request: Request):
    return employee_payload(request.app.state.tools.staff.transition(id, 'accepted'))


@router.post('/staff/calls/{id}/complete', dependencies=[Depends(staff)])
def complete(id: str, request: Request):
    return employee_payload(request.app.state.tools.staff.transition(id, 'completed'))


@router.post('/sessions/{id}/realtime')
async def realtime(id: str, request: Request, x_session_token: str = Header(default='')):
    record = request.app.state.sessions.authorized(id, x_session_token)
    if record['mode'] != 'voice':
        raise AppError('VOICE_MODE_REQUIRED', '音声モードで接客を開始してください。', 409)
    if request.headers.get('content-type', '').split(';')[0] != 'application/sdp':
        raise AppError('SDP_CONTENT_TYPE', '音声接続情報の形式が正しくありません。', 415)
    try:
        sdp = (await request.body()).decode('utf-8')
    except UnicodeDecodeError:
        raise AppError('INVALID_SDP', '音声接続情報が正しくありません。')
    answer = await request.app.state.realtime.connect(record, sdp)
    return Response(answer, media_type='application/sdp')


@router.post('/sessions/{id}/realtime/greet', response_model=CustomerGreeting)
async def greeting(id: str, request: Request, x_session_token: str = Header(default='')):
    request.app.state.sessions.authorized(id, x_session_token)
    result = await request.app.state.realtime.greet(id)
    return CustomerGreeting(status=result['status'])


@router.get('/sessions/{id}/voice-output', response_model=CustomerVoiceOutput)
def voice_output_config(id: str, request: Request, x_session_token: str = Header(default='')):
    request.app.state.sessions.authorized(id, x_session_token)
    return CustomerVoiceOutput(provider=request.app.state.realtime.output.mode.value)


@router.get('/sessions/{id}/voice-answer', response_model=CustomerVoiceAnswer | None)
def voice_answer(id: str, response_id: str, request: Request, x_session_token: str = Header(default='')):
    record = request.app.state.sessions.authorized(id, x_session_token)
    if len(response_id) > 200:
        raise AppError('INVALID_INPUT', '回答の識別情報を確認してください。')
    event = request.app.state.realtime.tts.latest(record, response_id)
    return CustomerVoiceAnswer(assistant_event_id=event['event_id'], display_text=event['text']) if event else None


@router.post('/sessions/{id}/speech/cancel', response_model=CustomerSpeechCancelled)
async def cancel_speech(id: str, request: Request, x_session_token: str = Header(default='')):
    request.app.state.sessions.authorized(id, x_session_token)
    await request.app.state.realtime.tts.cancel(id, clear_cache=False)
    return CustomerSpeechCancelled()


@router.post('/sessions/{id}/speech')
async def speech(id: str, body: CustomerSpeechInput, request: Request, x_session_token: str = Header(default='')):
    record = request.app.state.sessions.authorized(id, x_session_token)
    tts = request.app.state.realtime.tts
    task = asyncio.create_task(tts.render(record, body.assistant_event_id))
    try:
        while not task.done():
            if await request.is_disconnected():
                await tts.cancel(id)
                raise AppError('TTS_CANCELLED', '音声生成を停止しました。', 409)
            await asyncio.sleep(0.05)
        audio = await task
        return Response(audio.data, media_type=audio.content_type, headers={'Cache-Control': 'no-store',
            'X-Assistant-Event-Id': str(body.assistant_event_id), 'X-Audio-Test-Only': str(audio.test_only).lower()})
    finally:
        if not task.done():
            task.cancel()
            await tts.cancel(id)
        await asyncio.gather(task, return_exceptions=True)
