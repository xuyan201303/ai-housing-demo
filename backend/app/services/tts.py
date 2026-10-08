"""Authenticated event-bound TTS lifecycle. Cache at most the latest event/session."""
import asyncio
import hashlib
from app.models.domain import AppError, now
from app.services.knowledge_access import evidence_revision
from app.services.voice_output import VoiceMode

MAX_TEXT = 2000
FAILURE = '日本語音声生成に失敗しました。字幕はそのままご確認いただけます。音声を再試行するか、文字でご相談ください。'


class TtsService:
    def __init__(self, store, output):
        self.store, self.output = store, output
        self.jobs = {}
        self.cache = {}
        self.timeout = 30

    def answer(self, session, event_id):
        record = self.store.get('sessions', session['id'])
        if record['status'] != 'active':
            raise AppError('SESSION_ENDED', '接客は終了しています。', 409)
        revision = evidence_revision(self.store, record)
        voice = record.get('voice_output', {})
        if self.output.mode != VoiceMode.JAPANESE_TTS or voice.get('provider') != self.output.mode.value:
            raise AppError('TTS_MODE_REQUIRED', '日本語 TTS モードの音声接客が必要です。', 409)
        if voice.get('latest_event_id') != event_id:
            raise AppError('VOICE_EVENT_STALE', 'この回答は現在の音声再生対象ではありません。', 409)
        events = self.store.events(record['id'])
        event = next((e for e in events if e['event_id'] == event_id), None)
        if not event or event['kind'] != 'message' or event.get('role') != 'assistant' or event.get('provider') != 'openai_realtime_text':
            raise AppError('VOICE_EVENT_INVALID', '再生可能な回答が見つかりません。', 404)
        if any(e['kind'] == 'message' and e['event_id'] > event_id for e in events):
            raise AppError('VOICE_EVENT_STALE', '新しいご相談があるため、この回答の音声再生を停止しました。', 409)
        if (event.get('evidence_revision') != revision or event.get('voice_epoch') != voice.get('epoch')
                or event.get('property_id') != record.get('property_id') or event.get('version') != record['version']):
            raise AppError('VOICE_EVENT_STALE', '現在有効な資料・条件の回答をご確認ください。', 409)
        text = event.get('text', '')
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
            raise AppError('TTS_TEXT_LIMIT', 'この回答は音声生成の文字数上限を超えています。字幕をご確認ください。', 422)
        return event

    def latest(self, session, response_id):
        record = self.store.get('sessions', session['id'])
        eid = record.get('voice_output', {}).get('latest_event_id')
        if not eid:
            return None
        event = self.answer(session, eid)
        return event if event.get('response_id') == response_id else None

    async def render(self, session, event_id):
        event = self.answer(session, event_id)
        sid = session['id']
        if sid in self.cache and self.cache[sid][0] == event_id:
            return self.cache[sid][1]
        pending = self.jobs.get(sid)
        if pending:
            if pending[0] != event_id:
                raise AppError('TTS_BUSY', '前の音声生成を停止してから再試行してください。', 409)
            task = pending[1]
        else:
            self.cache.pop(sid, None)
            task = asyncio.create_task(self.generate(session, event))
            self.jobs[sid] = (event_id, task)
        try:
            audio = await asyncio.shield(task)
            self.answer(session, event_id)  # Recheck after remote latency, including expiry/end.
            self.cache[sid] = (event_id, audio)
            return audio
        except asyncio.CancelledError:
            raise AppError('TTS_CANCELLED', '音声再生を停止しました。', 409)
        finally:
            if task.done() and self.jobs.get(sid) == (event_id, task):
                self.jobs.pop(sid, None)

    async def generate(self, session, event):
        result = 'failed'
        try:
            audio = await asyncio.wait_for(self.output.adapter.synthesize(event['text']), timeout=self.timeout)
            result = 'completed'
            return audio
        except asyncio.CancelledError:
            result = 'cancelled'
            raise
        except Exception as exc:
            # Never return upstream body, resource keys, paths or debugging detail.
            raise AppError('TTS_FAILED', FAILURE, 502) from exc
        finally:
            self.store.event(session['id'], 'tts_usage', {'assistant_event_id': event['event_id'],
                'provider': self.output.mode.value, 'characters': len(event['text']),
                'display_text_sha256': hashlib.sha256(event['text'].encode()).hexdigest(),
                'status': result, 'created_at': now(), 'test_only': getattr(self.output.adapter, 'test_only', False)})

    async def cancel(self, session_id, *, clear_cache=True):
        pending = self.jobs.pop(session_id, None)
        if clear_cache:
            self.cache.pop(session_id, None)
        if pending:
            pending[1].cancel()
            await asyncio.gather(pending[1], return_exceptions=True)

    async def close_all(self):
        for sid in list(self.jobs):
            await self.cancel(sid)
        self.cache.clear()
