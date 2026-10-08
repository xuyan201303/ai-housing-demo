import secrets
import uuid
from datetime import date
from app.services.context import EMPTY_SNAPSHOT, validate_property, snapshot_for, raw_snapshot_for, customer_snapshot
from app.services.knowledge_access import BOUNDARY_VERSION, permission_stamp, available_snapshot, require_boundary
from app.models.domain import AppError, now


class SessionService:
    def __init__(self, store):
        self.store = store

    def start(self, mode, property_id=None):
        try:
            snapshot = self.store.latest()
        except AppError as exc:
            if exc.code != "NO_PUBLISHED_DATA": raise
            snapshot = dict(EMPTY_SNAPSHOT)
        allowed = available_snapshot(self.store, snapshot, date.fromisoformat(now()[:10]))
        if property_id: validate_property(allowed,property_id,date.fromisoformat(now()[:10]))
        record = {'id': uuid.uuid4().hex, 'token': secrets.token_urlsafe(32), 'version': snapshot['version'], 'mode': mode, 'property_id': property_id, 'status': 'active', 'created_at': now(), 'realtime': {'status': 'not_started'}, 'knowledge_boundary': BOUNDARY_VERSION, 'permission_stamp': permission_stamp(self.store, snapshot)}
        self.store.put('sessions', record)
        return dict(record, snapshot=customer_snapshot(record, allowed))

    def authorized(self, id, token, active=True, allow_legacy=False):
        record = self.store.get('sessions', id)
        if not token or not secrets.compare_digest(record['token'], token):
            raise AppError('SESSION_FORBIDDEN', '接客セッションの認証に失敗しました。', 403)
        if active and record['status'] != 'active':
            raise AppError('SESSION_ENDED', '接客は終了しています。新しい接客を開始してください。', 409)
        if not allow_legacy:
            require_boundary(self.store, record, raw_snapshot_for(self.store, record))
        return record

    def employee_view(self, record):
        events = self.store.events(record['id'])
        return employee_payload(dict(record, snapshot=raw_snapshot_for(self.store, record), messages=[e for e in events if e['kind'] == 'message'], tool_events=[e for e in events if e['kind'] == 'tool'], staff_calls=[c for c in self.store.list('staff_calls') if c['session_id'] == record['id']]))

    def view(self, record):
        # Internal compatibility only. Customer HTTP must use customer_view.
        result = self.employee_view(record)
        result['snapshot'] = employee_payload(customer_snapshot(record, snapshot_for(self.store, record)))
        return result

    def end(self, record):
        # Closing the sideband can update realtime state after authorization.
        # Preserve that completed close instead of writing the stale session copy.
        record = self.store.get('sessions', record['id'])
        record['status'] = 'ended'
        record['ended_at'] = now()
        self.store.put('sessions', record)
        return record


def employee_payload(value):
    """Keep authenticated audit details, never return credentials in logs/lists."""
    if isinstance(value, dict):
        return {k: employee_payload(v) for k, v in value.items() if k.lower() not in {'token', 'session_token', 'api_key', 'password', 'authorization'}}
    if isinstance(value, list): return [employee_payload(v) for v in value]
    return value
