"""Persistent, transactionally synchronized staff-call lifecycle."""
import json
import uuid

from app.models.domain import AppError, now


class StaffService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _event(db, session_id, action, record):
        # Same events table as Store.event, on the transaction's connection.
        # A nested Store.event would create a second connection and lock SQLite.
        payload = {'action': action, 'staff_call': record, 'created_at': now()}
        db.execute('INSERT INTO events(session_id,kind,payload) VALUES (?,?,?)', (session_id, 'staff', json.dumps(payload, ensure_ascii=False)))

    def call(self, session, reason, last_customer_question=''):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
            raise AppError('INVALID_STAFF_REASON', '呼出理由を500文字以内で入力してください。')
        if not isinstance(last_customer_question, str) or len(last_customer_question) > 2000:
            raise AppError('INVALID_STAFF_QUESTION', '直前の質問は2000文字以内で入力してください。')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM sessions WHERE id=?', (session['id'],)).fetchone()
            if not row:
                raise AppError('SESSION_NOT_FOUND', '接客セッションが見つかりません。', 404)
            persisted_session = json.loads(row['payload'])
            if persisted_session['status'] != 'active':
                raise AppError('SESSION_ENDED', '接客は終了しています。', 409)
            for row in db.execute('SELECT payload FROM staff_calls ORDER BY rowid DESC').fetchall():
                existing = json.loads(row['payload'])
                if existing['session_id'] == session['id'] and existing['status'] in {'pending', 'accepted'}:
                    return existing
            version = persisted_session['version']
            row = db.execute('SELECT payload FROM versions WHERE version=?', (version,)).fetchone()
            if version is not None and row is None:
                raise AppError('VERSION_NOT_FOUND', '接客の公開版が見つかりません。', 409)
            snapshot = json.loads(row['payload']) if row else {'property': {}}
            record = {
                'id': uuid.uuid4().hex, 'session_id': session['id'], 'version': version,
                'property_name': snapshot['property'].get('property_name', '住宅購入の一般相談') if persisted_session.get('property_id', True) else '住宅購入の一般相談', 'created_at': now(),
                'reason': reason.strip(), 'last_customer_question': last_customer_question,
                'status': 'pending', 'accepted_at': None, 'completed_at': None,
            }
            db.execute('INSERT INTO staff_calls(id,payload) VALUES (?,?)', (record['id'], json.dumps(record, ensure_ascii=False)))
            self._event(db, session['id'], 'created', record)
        return record

    def transition(self, id, status):
        if status not in {'accepted', 'completed'}:
            raise AppError('INVALID_STAFF_STATUS', '受付または対応完了を選択してください。')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM staff_calls WHERE id=?', (id,)).fetchone()
            if not row:
                raise AppError('NOT_FOUND', '呼出が見つかりません。', 404)
            record = json.loads(row['payload'])
            if record['status'] == status:
                return record
            expected = 'pending' if status == 'accepted' else 'accepted'
            if record['status'] != expected:
                raise AppError('INVALID_STAFF_TRANSITION', '受付後に対応完了できます。現在の状態を更新してください。', 409)
            record['status'] = status
            record['accepted_at' if status == 'accepted' else 'completed_at'] = now()
            db.execute('UPDATE staff_calls SET payload=? WHERE id=?', (json.dumps(record, ensure_ascii=False), id))
            self._event(db, record['session_id'], status, record)
        return record
