"""Small SQLite repository. Snapshots are immutable and session versions pinned."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from app.models.domain import AppError


class Store:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def init(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS versions(version INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS staff_calls(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS confirmations(id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS document_revisions(id TEXT PRIMARY KEY, document_id TEXT NOT NULL, confirmation_id INTEGER UNIQUE NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS publication_drafts(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS publication_submissions(idempotency_key TEXT PRIMARY KEY, draft_id TEXT NOT NULL, request_digest TEXT NOT NULL, version INTEGER NOT NULL);
            ''')

    def publication_schema_ready(self):
        with self.connect() as db:
            names = {r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {'document_revisions', 'publication_drafts', 'publication_submissions'}.issubset(names)

    def get(self, table: str, id: str):
        self._table(table)
        with self.connect() as db:
            row = db.execute(f'SELECT payload FROM {table} WHERE id=?', (id,)).fetchone()
        if not row:
            raise AppError('NOT_FOUND', '対象が見つかりません。', 404)
        return json.loads(row['payload'])

    def put(self, table: str, payload: dict):
        self._table(table)
        with self.connect() as db:
            db.execute(f'INSERT INTO {table}(id,payload) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (payload['id'], json.dumps(payload, ensure_ascii=False)))
        return payload

    def list(self, table: str):
        self._table(table)
        with self.connect() as db:
            rows = db.execute(f'SELECT payload FROM {table} ORDER BY rowid DESC').fetchall()
        return [json.loads(row['payload']) for row in rows]

    @staticmethod
    def _table(table):
        if table not in {'documents', 'sessions', 'staff_calls'}:
            raise ValueError('Invalid repository table')

    def latest(self):
        with self.connect() as db:
            row = db.execute('SELECT version,payload FROM versions ORDER BY version DESC LIMIT 1').fetchone()
        if not row:
            raise AppError('NO_PUBLISHED_DATA', '公開済みの資料がありません。管理画面で確認・公開してください。', 409)
        return dict(json.loads(row['payload']), version=row['version'])

    def version(self, version: int):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM versions WHERE version=?', (version,)).fetchone()
        if not row:
            raise AppError('VERSION_NOT_FOUND', '公開版が見つかりません。', 404)
        return dict(json.loads(row['payload']), version=version)

    def versions(self):
        with self.connect() as db:
            rows = db.execute('SELECT version,payload FROM versions ORDER BY version DESC').fetchall()
        return [dict(json.loads(r['payload']), version=r['version']) for r in rows]

    def event(self, session_id: str, kind: str, payload: dict):
        with self.connect() as db:
            cursor = db.execute('INSERT INTO events(session_id,kind,payload) VALUES (?,?,?)', (session_id, kind, json.dumps(payload, ensure_ascii=False)))
            return cursor.lastrowid

    def events(self, session_id: str):
        with self.connect() as db:
            rows = db.execute('SELECT id,kind,payload FROM events WHERE session_id=? ORDER BY id', (session_id,)).fetchall()
        return [dict(json.loads(r['payload']), event_id=r['id'], kind=r['kind']) for r in rows]
