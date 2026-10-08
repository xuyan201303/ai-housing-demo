"""OpenAI Realtime WebRTC with private tools on authenticated server sideband.

Official protocol: https://developers.openai.com/api/docs/guides/voice-webrtc?voice-api=realtime
https://developers.openai.com/api/docs/guides/voice-server-controls
No browser tool execution or client API key; no text-to-speech fake fallback.
"""
import asyncio
import json
import logging
import re
import uuid
import httpx
import websockets
from app.models.domain import AppError, now
from app.services.ai import INSTRUCTIONS, voice_instructions
from app.services.context import observe_customer
from app.services.ai_evidence import tool_evidence
from app.services.knowledge_access import evidence_revision, RESTART_MESSAGE
from app.services.tools import TOOL_DEFINITIONS
from app.services.guardrails import needs_loan_handoff, HANDOFF_MESSAGE, consultation_policy
from app.services.voice_output import voice_output, VoiceMode
from app.services.tts import TtsService


class RealtimeService:
    def __init__(self, store, tools, settings):
        self.store, self.tools, self.settings = store, tools, settings
        self.connections = {}
        self.connecting = set()
        self.output = voice_output(settings)
        self.tts = TtsService(store, self.output)

    async def interrupt_output(self, id):
        await self.tts.cancel(id)
        record = self.store.get('sessions', id)
        voice = record.get('voice_output', {})
        record['voice_output'] = {'provider': self.output.mode.value, 'epoch': voice.get('epoch', 0) + 1, 'latest_event_id': None}
        self.store.put('sessions', record)

    def save_text_answer(self, connection, response):
        if response.get('status') != 'completed' or not response.get('id'):
            return
        rid = response['id']
        seen = connection.setdefault('text_answers_seen', set())
        if rid in seen:
            return
        text = ''.join(part.get('text', '') for item in response.get('output', [])
                       if item.get('type') == 'message' and item.get('role') == 'assistant'
                       for part in item.get('content', []) if part.get('type') == 'output_text')
        if not text:
            text = ''.join(connection.get('text_parts', {}).get(rid, {}).values())
        if not text:
            return  # tool-only responses are not spoken
        self.ensure_context(connection)
        record = self.store.get('sessions', connection['session']['id'])
        voice = record.get('voice_output', {})
        if record['status'] != 'active' or connection.get('response_epoch') != voice.get('epoch'):
            return  # a late completed answer after barge-in must never be replayed
        seen.add(rid)
        eid = self.store.event(record['id'], 'message', {'role': 'assistant', 'text': text,
            'created_at': now(), 'channel': 'voice', 'references': connection['references'],
            'version': record['version'], 'property_id': record.get('property_id'),
            'provider': 'openai_realtime_text', 'response_id': rid, 'voice_epoch': voice['epoch'],
            'evidence_revision': evidence_revision(self.store, record)})
        record['voice_output']['latest_event_id'] = eid
        self.store.put('sessions', record)
        connection.get('text_parts', {}).pop(rid, None)

    def status(self, session_id, status, **extra):
        record = self.store.get('sessions', session_id)
        record['realtime'] = {'status': status, **extra}
        self.store.put('sessions', record)

    async def connect(self, session, sdp):
        if not self.settings.api_key:
            raise AppError('OPENAI_NOT_CONFIGURED', 'OpenAI API Key が未設定です。音声接客を利用できません。', 503)
        if not sdp.startswith('v=0') or len(sdp) > 150000:
            raise AppError('INVALID_SDP', '音声接続情報が正しくありません。')
        id = session['id']
        if id in self.connections or id in self.connecting:
            raise AppError('VOICE_ALREADY_CONNECTED', '音声接客はすでに接続中です。', 409)
        self.connecting.add(id)
        self.status(id, 'connecting')
        await self.interrupt_output(id)
        call_id = None
        try:
            overview = self.tools.execute(session, 'get_consultation_context', {})
            config = {
                'type': 'realtime', 'model': self.settings.realtime_model,
                'instructions': voice_instructions(),
                'output_modalities': self.output.modalities,
                'audio': {'input': {'transcription': {'model': 'gpt-4o-mini-transcribe', 'language': 'ja'}, 'turn_detection': {'type': 'server_vad', 'create_response': False, 'interrupt_response': True}}, 'output': {'voice': getattr(self.settings, 'realtime_voice', 'marin')}},
                'tools': [{k: v for k, v in t.items() if k != 'strict'} for t in TOOL_DEFINITIONS],
                'tool_choice': 'auto',
            }
            if self.output.mode == VoiceMode.JAPANESE_TTS:
                config['audio'].pop('output')
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post('https://api.openai.com/v1/realtime/calls', headers={'Authorization': f'Bearer {self.settings.api_key}'}, files={'sdp': (None, sdp, 'application/sdp'), 'session': (None, json.dumps(config), 'application/json')})
            if response.is_error:
                raise AppError('REALTIME_HTTP_' + str(response.status_code), 'OpenAI 音声接続に失敗しました。設定・利用上限を確認してください。', 502)
            call_id = response.headers.get('location', '').rstrip('/').split('/')[-1]
            if not re.fullmatch(r'rtc_[A-Za-z0-9_-]+', call_id):
                raise AppError('REALTIME_CALL_ID', '音声接続の管理IDを受信できませんでした。', 502)
            if self.store.get('sessions', id)['status'] != 'active':
                raise AppError('SESSION_ENDED', '接客が終了したため音声接続を中止しました。', 409)
            socket = await websockets.connect('wss://api.openai.com/v1/realtime?call_id=' + call_id, additional_headers={'Authorization': f'Bearer {self.settings.api_key}'}, open_timeout=15, max_size=2000000)
            if self.store.get('sessions', id)['status'] != 'active':
                await socket.close()
                raise AppError('SESSION_ENDED', '接客が終了したため音声接続を中止しました。', 409)
            connection = {'socket': socket, 'call_id': call_id, 'greeted': False, 'seen': set(), 'turns': 0, 'tool_count': 0, 'session': session, 'references': overview['references'], 'active_response': False, 'pending_response': None, 'continue_tools': False}
            self.connections[id] = connection
            await self.send_evidence(connection, 'get_consultation_context', overview)
            connection['task'] = asyncio.create_task(self.listen(connection))
            self.status(id, 'connected')
            return response.text
        except AppError:
            self.status(id, 'error', error={'code': 'REALTIME_CONNECT_FAILED', 'message': '音声接続に失敗しました。'})
            if call_id:
                await self.hangup(call_id)
            raise
        except (httpx.HTTPError, OSError, websockets.exceptions.WebSocketException) as exc:
            self.status(id, 'error', error={'code': 'REALTIME_CONNECTION', 'message': '音声サービスとの通信に失敗しました。'})
            if call_id:
                await self.hangup(call_id)
            raise AppError('REALTIME_CONNECTION', '音声サービスとの通信に失敗しました。文字接客をご利用ください。', 502) from exc
        finally:
            self.connecting.discard(id)

    async def greet(self, id):
        if self.store.get('sessions', id)['status'] != 'active':
            raise AppError('SESSION_ENDED', '接客は終了しています。', 409)
        connection = self.connections.get(id)
        if not connection:
            raise AppError('VOICE_NOT_CONNECTED', '音声接続がありません。', 409)
        if not connection['greeted']:
            connection['greeted'] = True
            overview = self.tools.execute(connection['session'], 'get_consultation_context', {})
            await self.request_response(connection, {
                'tool_choice': 'none',
                'instructions': INSTRUCTIONS + '\n最初は「こんにちは。AI住宅コンシェルジュです。」から始め、住宅購入・購入の流れ・住宅ローンなど自由に相談できると短く歓迎してください。特定物件の名前・価格・設備を紹介しない。',
            })
        return {'status': 'greeting_requested'}

    async def request_response(self, connection, response):
        self.ensure_context(connection)
        response = dict(response)
        task = response.get('instructions', '')
        if task.startswith(INSTRUCTIONS):
            task = task[len(INSTRUCTIONS):].lstrip()
        response['instructions'] = voice_instructions(task)
        if self.output.mode == VoiceMode.JAPANESE_TTS:
            response['output_modalities'] = ['text']
        if connection['active_response']:
            connection['pending_response'] = response
            return
        connection['active_response'] = True
        await connection['socket'].send(json.dumps({'type': 'response.create', 'response': response}))

    async def send_evidence(self, connection, name, raw):
        """Official user/input_text data channel, never a system instruction.

        Replace our prior data item each turn; assistant/tool history must not be
        reused after the permitted source set changes (requires a fresh Session).
        """
        self.ensure_context(connection)
        payload = tool_evidence(self.store, connection['session'], name, raw, query=connection.get('query', ''))
        previous = connection.get('evidence_item_id')
        if previous:
            await connection['socket'].send(json.dumps({'type': 'conversation.item.delete', 'item_id': previous}))
        item_id = 'evidence_' + uuid.uuid4().hex
        connection['evidence_item_id'] = item_id
        await connection['socket'].send(json.dumps({'type': 'conversation.item.create', 'item': {
            'id': item_id, 'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': json.dumps({'current_evidence': payload}, ensure_ascii=False)}]}}))

    def ensure_context(self, connection):
        # Permission revocation is checked by snapshot_for. Expiry can also make
        # provider-side assistant/tool history unsafe, so do not reuse that call.
        # Explicit property selection is independent of source eligibility.
        signature = evidence_revision(self.store, connection['session'])
        previous = connection.setdefault('context_signature', signature)
        if previous != signature:
            raise AppError('SESSION_RESTART_REQUIRED', RESTART_MESSAGE, 409)

    async def listen(self, connection):
        session = connection['session']; id = session['id']; ws = connection['socket']
        try:
            async for raw in ws:
                event = json.loads(raw)
                type = event.get('type')
                if type == 'input_audio_buffer.speech_started' and self.output.mode == VoiceMode.JAPANESE_TTS:
                    await self.interrupt_output(id)
                elif type == 'conversation.item.input_audio_transcription.completed':
                    text = event.get('transcript', '')
                    if not text.strip():
                        continue
                    connection['query'] = text
                    session=observe_customer(self.store,session,text);connection['session']=session
                    connection['turns'] += 1; connection['tool_count'] = 0
                    self.store.event(id, 'message', {'role': 'user', 'text': text, 'created_at': now(), 'channel': 'voice'})
                    if needs_loan_handoff(text):
                        connection['references'] = []
                        call = await asyncio.to_thread(self.tools.execute, session, 'call_staff', {'reason': '住宅ローン審査の判断依頼', 'last_customer_question': text})
                        await self.send_evidence(connection, 'call_staff', call)
                        response = {'instructions': 'この質問への回答は次の方針説明だけにしてください。融資可否の判断をしない。' + HANDOFF_MESSAGE}
                    else:
                        # Revalidate the pinned version's lifetime on every voice turn.
                        overview = await asyncio.to_thread(self.tools.execute, session, 'get_consultation_context', {})
                        policy = consultation_policy(session, overview, text)
                        connection['references'] = [] if policy else overview['references']
                        await self.send_evidence(connection, 'get_consultation_context', overview)
                        response = {'tool_choice':'none', 'instructions':'次の確認済み方針説明だけを読み上げてください: '+policy} if policy else {}
                    await self.request_response(connection, response)
                elif type == 'response.created':
                    connection['active_response'] = True
                    connection['response_epoch'] = self.store.get('sessions', id).get('voice_output', {}).get('epoch')
                elif type in {'response.output_text.delta', 'response.output_text.done'} and self.output.mode == VoiceMode.JAPANESE_TTS:
                    rid = event.get('response_id')
                    if rid:
                        parts = connection.setdefault('text_parts', {}).setdefault(rid, {})
                        key = (event.get('item_id'), event.get('content_index', 0))
                        parts[key] = event.get('text', '') if type.endswith('.done') else parts.get(key, '') + event.get('delta', '')
                elif type == 'response.function_call_arguments.done':
                    self.ensure_context(connection)
                    call_id = event.get('call_id')
                    if not call_id or call_id in connection['seen']:
                        continue
                    connection['seen'].add(call_id); connection['tool_count'] += 1
                    try:
                        if connection['tool_count'] > 8:
                            raise AppError('TOOL_LIMIT', 'ツール呼出上限に達しました。スタッフへお尋ねください。')
                        result = await asyncio.to_thread(self.tools.execute, session, event['name'], json.loads(event['arguments']), ai_requested=True)
                    except (AppError, ValueError, TypeError) as exc:
                        result = {'error': {'code': getattr(exc, 'code', 'TOOL_ARGUMENTS'), 'message': getattr(exc, 'message', 'ツール入力が正しくありません。')}}
                    connection['references'] = result.get('references', connection['references'])
                    safe_result = tool_evidence(self.store, session, event['name'], result)
                    await ws.send(json.dumps({'type': 'conversation.item.create', 'item': {'type': 'function_call_output', 'call_id': call_id, 'output': json.dumps(safe_result, ensure_ascii=False)}}))
                    connection['continue_tools'] = True
                elif type in {'response.output_audio_transcript.done', 'response.audio_transcript.done'} and self.output.mode == VoiceMode.OPENAI_REALTIME_AUDIO:
                    self.store.event(id, 'message', {'role': 'assistant', 'text': event.get('transcript', ''), 'created_at': now(), 'channel': 'voice', 'references': connection['references'], 'version': session['version'], 'provider': 'openai_realtime'})
                elif type == 'error':
                    self.status(id, 'error', error={'code': 'REALTIME_PROTOCOL', 'message': '音声APIがエラーを返しました。接客を終了して再接続してください。'})
                    break
                elif type == 'response.done':
                    connection['active_response'] = False
                    response = event.get('response', {})
                    if self.output.mode == VoiceMode.JAPANESE_TTS:
                        self.save_text_answer(connection, response)
                        connection.get('text_parts', {}).pop(response.get('id'), None)
                    self.store.event(id, 'realtime_response', {'status': response.get('status'), 'usage': response.get('usage'), 'created_at': now()})
                    if response.get('status') == 'failed':
                        self.status(id, 'error', error={'code': 'REALTIME_RESPONSE_FAILED', 'message': '音声回答に失敗しました。'})
                    elif connection['pending_response'] is not None:
                        pending = connection['pending_response']; connection['pending_response'] = None; connection['continue_tools'] = False
                        await self.request_response(connection, pending)
                    elif connection['continue_tools']:
                        connection['continue_tools'] = False
                        if connection['tool_count'] <= 8:
                            await self.request_response(connection, {})
                        else:
                            self.status(id, 'error', error={'code': 'REALTIME_TOOL_LIMIT', 'message': 'ツール呼出上限に達しました。スタッフをお呼びください。'})
                            break
        except asyncio.CancelledError:
            raise
        except Exception:
            if not connection.get('closing'):
                self.status(id, 'error', error={'code': 'REALTIME_SIDEBAND', 'message': '音声制御の接続が切れました。接客を終了してください。'})
        finally:
            if self.connections.get(id) is connection and not connection.get('closing'):
                self.connections.pop(id, None)
                if self.store.get('sessions', id).get('realtime', {}).get('status') != 'error':
                    self.status(id, 'disconnected')
                await ws.close()
                await self.tts.cancel(id)
                await self.hangup(connection['call_id'])

    async def hangup(self, call_id):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(f'https://api.openai.com/v1/realtime/calls/{call_id}/hangup', headers={'Authorization': f'Bearer {self.settings.api_key}'})
                # Save failures honestly; do not silently retry connection creation.
                return response.status_code
        except httpx.HTTPError as exc:
            logging.getLogger(__name__).warning('Realtime hangup transport failed (%s)', type(exc).__name__)
            return None

    async def close(self, id):
        await self.tts.cancel(id)
        connection = self.connections.pop(id, None)
        if not connection:
            return
        connection['closing'] = True
        self.status(id, 'closing')
        # End the actual call while its WebRTC / sideband are still alive.
        # The client silences media first and closes its peer after this response.
        status = await self.hangup(connection['call_id'])
        await connection['socket'].close()
        connection['task'].cancel()
        await asyncio.gather(connection['task'], return_exceptions=True)
        self.status(id, 'closed', upstream_hangup_status=status)

    async def close_all(self):
        for id in list(self.connections):
            await self.close(id)
        await self.tts.close_all()
