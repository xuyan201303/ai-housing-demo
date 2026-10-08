import hashlib
import copy
import json
import math
import re
import uuid
from datetime import date
from pathlib import Path
from app.models.domain import AppError, now
from app.services.document_sdk_adapter import DocumentSdkAdapter, PROPERTY_KEYS


class DocumentService:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        self.adapter = DocumentSdkAdapter()

    @staticmethod
    def list_item(record):
        """The list needs draft status, not another copy of the entire draft."""
        result = {k: v for k, v in record.items() if k not in {'raw', 'normalized', 'reviewed', 'draft'}}
        draft = record.get('draft')
        result['has_draft'] = bool(draft and not draft.get('confirmed_at'))
        result['draft_saved_at'] = draft.get('saved_at') if draft else None
        result['draft_revision'] = draft.get('revision', 0) if draft else 0
        return result

    @staticmethod
    def source_revision(record):
        # File identity alone does not detect a concurrent business confirmation.
        basis = {key: record.get(key) for key in ('id', 'sha256', 'parsed_at', 'status', 'usage',
                                                 'usage_changed_at', 'confirmation_id', 'published_version', 'update_cancelled')}
        return hashlib.sha256(json.dumps(basis, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def _draft_view(self, record):
        draft = record.get('draft') or {}
        candidate = draft if draft and not draft.get('confirmed_at') else {}
        return {'document_id': record['id'], 'document_sha256': record.get('sha256', ''),
                'source_revision': self.source_revision(record),
                'base_confirmation_id': record.get('confirmation_id'),
                'base_published_version': record.get('published_version'),
                'revision': draft.get('revision', 0),
                'reviewed': copy.deepcopy(candidate.get('reviewed', record.get('reviewed', record.get('normalized', {})))),
                'usage': candidate.get('usage', record.get('latest_revision_usage', record.get('usage', 'unclassified'))),
                'note': candidate.get('note', record.get('confirmation_note', '')), 'saved_at': draft.get('saved_at'),
                'saved_by': draft.get('saved_by'), 'confirmed_at': draft.get('confirmed_at'),
                'stale': bool(draft and not draft.get('confirmed_at') and draft.get('source_revision') != self.source_revision(record))}

    @staticmethod
    def _require_parsed(record):
        if record.get('update_cancelled'): raise AppError('CANCELLED_UPDATE', 'この更新は取り消されています。元資料から更新を準備し直してください。', 409)
        if record['status'] not in {'parsed', 'confirmed', 'published'}:
            raise AppError('INVALID_STATE', '資料を解析してから編集してください。', 409)

    def get_draft(self, id):
        record = self.store.get('documents', id)
        self._require_parsed(record)
        return self._draft_view(record)

    def _check_draft_basis(self, record, document_sha256, source_revision, revision):
        if not record.get('sha256') or document_sha256 != record['sha256']:
            raise AppError('DRAFT_DOCUMENT_MISMATCH', '編集対象の資料が一致しません。資料を開き直してください。', 409)
        if source_revision != self.source_revision(record):
            raise AppError('DRAFT_SOURCE_CHANGED', '資料の確認・公開状態が更新されました。内容を読み直してから保存してください。', 409)
        if revision != (record.get('draft') or {}).get('revision', 0):
            raise AppError('DRAFT_CONFLICT', '別の画面で下書きが更新されました。資料を開き直してください。', 409)

    def save_draft(self, id, reviewed, note, usage, document_sha256, source_revision, revision, actor='admin', resume_cancelled=False):
        if usage not in {'customer', 'internal', 'unclassified'}:
            raise AppError('INVALID_DOCUMENT_USAGE', '資料用途を確認してください。', field_errors={'usage': '資料用途を選択してください。'})
        self._validate_form_fields(reviewed, complete=False)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM documents WHERE id=?', (id,)).fetchone()
            if not row: raise AppError('NOT_FOUND', '資料が見つかりません。', 404)
            record = json.loads(row['payload'])
            if resume_cancelled and record.get('update_cancelled'):
                self._require_parsed(dict(record, update_cancelled=False))
            else:
                self._require_parsed(record)
            self._check_draft_basis(record, document_sha256, source_revision, revision)
            if resume_cancelled and record.get('update_cancelled'):
                record.pop('update_cancelled', None)
                source_revision = self.source_revision(record)
            # Draft values are independent of SDK facts and the current approval.
            record['draft'] = {'document_id': id, 'document_sha256': document_sha256,
                               'source_revision': source_revision, 'base_confirmation_id': record.get('confirmation_id'),
                               'base_published_version': record.get('published_version'), 'revision': revision + 1,
                               'reviewed': copy.deepcopy(reviewed), 'usage': usage, 'note': note,
                               'saved_at': now(), 'saved_by': actor, 'confirmed_at': None}
            db.execute('UPDATE documents SET payload=? WHERE id=?', (json.dumps(record, ensure_ascii=False), id))
        return self._draft_view(record)

    def confirm_draft(self, id, note, document_sha256, source_revision, revision, actor='admin'):
        """Append an immutable revision. Publication keeps its original approval."""
        if not isinstance(note, str) or not note.strip():
            raise AppError('CONFIRMATION_NOTE_REQUIRED', '確認内容を入力してください。', field_errors={'note': '確認内容を入力してください。'})
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM documents WHERE id=?', (id,)).fetchone()
            if not row: raise AppError('NOT_FOUND', '資料が見つかりません。', 404)
            record = json.loads(row['payload'])
            self._require_parsed(record)
            self._check_draft_basis(record, document_sha256, source_revision, revision)
            draft = record.get('draft')
            if not draft or draft.get('confirmed_at'):
                raise AppError('DRAFT_REQUIRED', '編集内容を下書きとして保存してから確認してください。', 409)
            if draft.get('source_revision') != self.source_revision(record):
                raise AppError('DRAFT_SOURCE_CHANGED', '資料の確認・公開状態が更新されました。下書きを保存し直してから確認してください。', 409)
            reviewed = self.validate_review(copy.deepcopy(draft['reviewed']), record)
            self._write_confirmation(db, record, reviewed, note, draft['usage'], actor)
            draft.update(reviewed=copy.deepcopy(reviewed), confirmed_at=record['confirmed_at'],
                         source_revision=self.source_revision(record), base_confirmation_id=record['confirmation_id'],
                         base_published_version=record.get('published_version'))
            db.execute('UPDATE documents SET payload=? WHERE id=?', (json.dumps(record, ensure_ascii=False), id))
        return record

    @staticmethod
    def _preserve_previous_confirmation(db, record):
        cid = record.get('confirmation_id')
        if not cid or record.get('usage') != 'customer': return
        existing = db.execute('SELECT id FROM document_revisions WHERE confirmation_id=? AND document_id=?', (cid, record['id'])).fetchone()
        if existing: return
        row = db.execute('SELECT payload FROM confirmations WHERE id=? AND document_id=?', (cid, record['id'])).fetchone()
        if not row: return
        proof = json.loads(row['payload'])
        # Only an actually current, unrevoked legacy proof may be retained.
        if (proof.get('event') != 'business_confirmation' or proof.get('usage') != 'customer' or
            not proof.get('actor') or not proof.get('confirmed_at') or
            (record.get('usage_changed_at') and record['usage_changed_at'] > proof['confirmed_at'])): return
        rid = uuid.uuid4().hex
        value = {'revision_id': rid, 'document_id': record['id'], 'confirmation_id': cid,
                 'usage_epoch': record.get('usage_epoch', 0), 'usage': proof['usage'],
                 'confirmed_at': proof['confirmed_at'], 'actor': proof['actor'], 'note': proof.get('note', ''),
                 'cancelled': False, 'legacy_association': True}
        db.execute('INSERT INTO document_revisions VALUES (?,?,?,?)', (rid, record['id'], cid, json.dumps(value, ensure_ascii=False)))

    @staticmethod
    def _write_confirmation(db, record, reviewed, note, usage, actor):
        previous_confirmation = record.get('confirmation_id')
        DocumentService._preserve_previous_confirmation(db, record)
        # Ordinary edits prepare a candidate; only set_usage explicitly revokes all approvals.
        effective_usage = record.get('usage') if previous_confirmation and record.get('usage') == 'customer' else usage
        rid = uuid.uuid4().hex
        epoch = record.get('usage_epoch', 0)
        record.update(reviewed=reviewed, confirmation_note=note, status='confirmed', confirmed_at=now(),
                      usage=effective_usage, latest_revision_usage=usage, confirmed_by=actor, latest_revision_id=rid)
        event = {'event': 'business_confirmation', 'usage': usage, 'actor': actor, 'reviewed': reviewed, 'note': note,
                 'confirmed_at': record['confirmed_at'], 'revision_id': rid, 'usage_epoch': epoch,
                 'raw_sha256': hashlib.sha256(json.dumps(record['raw'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
        if previous_confirmation: event['supersedes_confirmation_id'] = previous_confirmation
        cursor = db.execute('INSERT INTO confirmations(document_id,payload) VALUES (?,?)', (record['id'], json.dumps(event, ensure_ascii=False)))
        record['confirmation_id'] = cursor.lastrowid
        value = {'revision_id': rid, 'document_id': record['id'], 'confirmation_id': cursor.lastrowid,
                 'usage_epoch': epoch, 'usage': usage, 'confirmed_at': record['confirmed_at'], 'actor': actor,
                 'note': note, 'cancelled': False, 'replaces_document_id': record.get('replaces_document_id'),
                 'replaces_confirmation_id': record.get('replaces_confirmation_id')}
        db.execute('INSERT INTO document_revisions VALUES (?,?,?,?)', (rid, record['id'], cursor.lastrowid, json.dumps(value, ensure_ascii=False)))

    def revisions(self, id):
        record = self.store.get('documents', id)
        with self.store.connect() as db:
            rows = db.execute('SELECT payload FROM document_revisions WHERE document_id=? ORDER BY rowid DESC', (id,)).fetchall()
            result = [json.loads(row['payload']) for row in rows]
        versions = self.store.versions()
        for item in result:
            item['revoked'] = item.get('usage_epoch', 0) != record.get('usage_epoch', 0) or record.get('usage') != 'customer'
            item['published_versions'] = [v['version'] for v in versions if v.get('document_approvals', {}).get(id) == item['confirmation_id']]
        return result

    def begin_revision(self, id, reason, actor='admin'):
        if not reason.strip(): raise AppError('REVISION_REASON_REQUIRED', '修正理由を入力してください。', field_errors={'reason': '修正理由を入力してください。'})
        record = self.store.get('documents', id)
        if record.get('update_cancelled') and record['status'] not in {'parsed', 'confirmed', 'published'}:
            raise AppError('CANCELLED_UPDATE', '取り消したアップロードは再利用できません。元資料から新しいファイルを準備してください。', 409)
        self._require_parsed(dict(record, update_cancelled=False))
        draft = record.get('draft') or {}
        if draft and not draft.get('confirmed_at') and not draft.get('cancelled'):
            raise AppError('ACTIVE_DOCUMENT_DRAFT', '保存済みの下書きを開くか、取り消してから新しい修訂を準備してください。', 409)
        basis = self._draft_view(record)
        return self.save_draft(id, basis['reviewed'], reason, record.get('latest_revision_usage', record['usage']),
                               basis['document_sha256'], basis['source_revision'], basis['revision'], actor, resume_cancelled=True)

    def cancel_update(self, id, actor='admin'):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM documents WHERE id=?', (id,)).fetchone()
            if not row: raise AppError('NOT_FOUND', '資料が見つかりません。', 404)
            record = json.loads(row['payload']); draft = record.get('draft') or {}
            if not draft:
                if not record.get('replaces_document_id') or record.get('published_version'):
                    raise AppError('DRAFT_REQUIRED', '取り消せる更新がありません。', 409)
                record.update(update_cancelled=True, update_cancelled_at=now(), update_cancelled_by=actor)
                db.execute('UPDATE documents SET payload=? WHERE id=?', (json.dumps(record, ensure_ascii=False), id))
                return record

            if draft.get('confirmed_at'):
                cid = draft.get('base_confirmation_id')
                if cid != record.get('confirmation_id'): raise AppError('UPDATE_CHANGED', '確認修訂が別の画面で変更されました。資料を開き直してください。', 409)
                published = [json.loads(v['payload']) for v in db.execute('SELECT payload FROM versions')]
                if any(v.get('document_approvals', {}).get(id) == cid for v in published):
                    raise AppError('PUBLISHED_REVISION', '公開版で使用中の修訂は取り消せません。公開内容の変更で対象を外してください。', 409)
                revrow = db.execute('SELECT id,payload FROM document_revisions WHERE confirmation_id=?', (cid,)).fetchone()
                if revrow:
                    rev = json.loads(revrow['payload']); rev.update(cancelled=True, cancelled_at=now(), cancelled_by=actor)
                    db.execute('UPDATE document_revisions SET payload=? WHERE id=?', (json.dumps(rev, ensure_ascii=False), revrow['id']))
            if draft.get('confirmed_at'):
                prior_rows = db.execute('SELECT confirmation_id,payload,id FROM document_revisions WHERE document_id=? AND confirmation_id<>? ORDER BY rowid DESC', (id, record.get('confirmation_id'))).fetchall()
                restored = False
                for prior in prior_rows:
                    assoc = json.loads(prior['payload'])
                    if assoc.get('cancelled') or assoc.get('usage_epoch', 0) != record.get('usage_epoch', 0): continue
                    proofrow = db.execute('SELECT payload FROM confirmations WHERE id=? AND document_id=?', (prior['confirmation_id'], id)).fetchone()
                    proof = json.loads(proofrow['payload'])
                    record.update(confirmation_id=prior['confirmation_id'], latest_revision_id=prior['id'], reviewed=proof['reviewed'],
                                  latest_revision_usage=proof['usage'], confirmation_note=proof.get('note', ''), confirmed_at=proof['confirmed_at'], confirmed_by=proof['actor'])
                    restored = True
                    break
                if not restored:
                    record.update(confirmation_id=None, latest_revision_id=None, status='parsed', confirmed_at=None)
                    record.pop('reviewed', None)
                    record.pop('latest_revision_usage', None)
            draft.update(cancelled=True, confirmed_at=draft.get('confirmed_at') or now(), cancelled_at=now(), cancelled_by=actor)
            db.execute('UPDATE documents SET payload=? WHERE id=?', (json.dumps(record, ensure_ascii=False), id))
        return record

    def duplicates(self, sha256):
        return [self.list_item(r) for r in self.store.list('documents') if r.get('sha256') == sha256]

    def upload(self, filename: str, content: bytes, duplicate_action="check", replaces_document_id=None, replaces_confirmation_id=None, reuse_document_id=None):
        # Filename is presentation-only; physical storage always UUID.
        filename = filename.replace('\\', '/').split('/')[-1]
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)[:180]
        suffix = Path(filename).suffix.lower()
        if suffix not in {'.pdf', '.xlsx'}:
            raise AppError('UNSUPPORTED_FILE', 'PDF / XLSX のみアップロードできます。', 415)
        if not content or len(content) > self.settings.max_upload_bytes:
            raise AppError('UPLOAD_SIZE', '空ファイルまたはサイズ上限を超えています。', 413)
        if (suffix == '.pdf' and not content.startswith(b'%PDF-')) or (suffix == '.xlsx' and not content.startswith(b'PK\x03\x04')):
            raise AppError('FILE_SIGNATURE', '拡張子とファイル形式が一致しません。', 415)
        matches = self.duplicates(hashlib.sha256(content).hexdigest())
        if duplicate_action not in {'check', 'reuse', 'separate'}: raise AppError('INVALID_DUPLICATE_ACTION', '同じ資料の扱いを選択してください。')
        if replaces_document_id:
            if replaces_confirmation_id is None: raise AppError('REPLACEMENT_MISMATCH', '差し替え対象の確認修訂を選択してください。', 409)
            old = self.store.get('documents', replaces_document_id)
            if replaces_confirmation_id is not None:
                with self.store.connect() as db:
                    if not db.execute('SELECT id FROM confirmations WHERE id=? AND document_id=?', (replaces_confirmation_id, replaces_document_id)).fetchone():
                        raise AppError('REPLACEMENT_MISMATCH', '差し替え対象の確認修訂が一致しません。', 409)
        if matches and duplicate_action == 'check':
            raise AppError('DUPLICATE_FILE', '同じ内容の資料が登録されています。既存資料を使用するか、別資料として保存するか選択してください。', 409)
        if duplicate_action == 'reuse':
            if not matches: raise AppError('DUPLICATE_NOT_FOUND', '再利用できる同じ資料がありません。', 409)
            chosen = next((r for r in matches if r['id'] == reuse_document_id), None) if reuse_document_id else (matches[0] if len(matches) == 1 else None)
            if not chosen: raise AppError('DUPLICATE_SELECTION_REQUIRED', '再利用する資料を明確に選択してください。', 409)
            return dict(self.store.get('documents', chosen['id']), reused=True,
                        replacement_hint={'document_id': replaces_document_id, 'confirmation_id': replaces_confirmation_id})
        id = uuid.uuid4().hex
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        (self.settings.upload_dir / (id + suffix)).write_bytes(content)
        record = {'id': id, 'filename': filename, 'suffix': suffix, 'sha256': hashlib.sha256(content).hexdigest(), 'size_bytes': len(content), 'status': 'uploaded', 'usage': 'unclassified', 'created_at': now(), 'parsed_at': None, 'confirmed_at': None, 'published_version': None, 'error': None}
        record.update(replaces_document_id=replaces_document_id, replaces_confirmation_id=replaces_confirmation_id)
        return self.store.put('documents', record)

    def parse(self, id):
        record = self.store.get('documents', id)
        if record.get('update_cancelled'): raise AppError('CANCELLED_UPDATE', '取り消した更新は解析できません。元資料から更新を準備し直してください。', 409)
        if record['status'] != 'uploaded':
            raise AppError('INVALID_STATE', '解析は新しいアップロードに対して実行してください。', 409)
        try:
            result = self.adapter.parse(self.settings.upload_dir / (id + record['suffix']), id, record['filename'])
        except AppError as exc:
            record.update(status='error', error={'code': exc.code, 'message': exc.message})
            self.store.put('documents', record)
            raise
        record.update(result, status='parsed', parsed_at=now())
        return self.store.put('documents', record)

    def set_usage(self, id, usage, note, actor='admin'):
        if usage not in {'customer', 'internal', 'unclassified'}:
            raise AppError('INVALID_DOCUMENT_USAGE', '資料用途を確認してください。')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM documents WHERE id=?', (id,)).fetchone()
            if not row: raise AppError('NOT_FOUND', '資料が見つかりません。', 404)
            record = json.loads(row['payload'])
            if record['status'] not in {'parsed', 'confirmed', 'published'}:
                raise AppError('INVALID_STATE', '解析後に用途を確認してください。', 409)
            # Even choosing customer never grants approval. An actual new review is required.
            record.update(usage_epoch=record.get('usage_epoch', 0) + 1, usage=usage, status='parsed', confirmed_at=None, confirmation_id=None,
                          usage_changed_at=now(), usage_changed_by=actor)
            db.execute('INSERT INTO confirmations(document_id,payload) VALUES (?,?)', (id, json.dumps(
                {'event': 'usage_changed', 'usage': usage, 'note': note, 'actor': actor, 'changed_at': now()}, ensure_ascii=False)))
            db.execute('UPDATE documents SET payload=? WHERE id=?', (json.dumps(record, ensure_ascii=False), id))
        return record

    def confirm(self, id, reviewed, note, usage='unclassified', actor='admin'):
        if usage not in {'customer', 'internal', 'unclassified'}:
            raise AppError('INVALID_DOCUMENT_USAGE', '資料用途を確認してください。')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM documents WHERE id=?', (id,)).fetchone()
            if not row: raise AppError('NOT_FOUND', '資料が見つかりません。', 404)
            record = json.loads(row['payload'])
            if record.get('update_cancelled'): raise AppError('CANCELLED_UPDATE', 'この更新は取り消されています。更新を準備し直してください。', 409)
            if record['status'] != 'parsed':
                raise AppError('INVALID_STATE', '解析済み資料の用途と内容を確認してください。保存済み用途は先に旧確認を無効化します。', 409)
            reviewed = self.validate_review(copy.deepcopy(reviewed), record)
            self._write_confirmation(db, record, reviewed, note, usage, actor)
            db.execute('UPDATE documents SET payload=? WHERE id=?', (json.dumps(record, ensure_ascii=False), id))
        return record

    @staticmethod
    def _validate_form_fields(reviewed, complete=False):
        """Drafts may be incomplete. Present values still need safe business types."""
        fields = {}
        codes = []
        def invalid(path, message, code):
            fields[path] = message
            codes.append(code)
        if not isinstance(reviewed, dict):
            raise AppError('INVALID_INPUT', '編集内容を確認してください。', field_errors={'reviewed': '編集内容を確認してください。'})
        unknown = set(reviewed) - {'document', 'property', 'knowledge', 'faq', 'rates'}
        for key in unknown:
            invalid(key, '対応していない項目です。', 'INVALID_INPUT')
        for section in ('document', 'property'):
            if not isinstance(reviewed.get(section, {}), dict):
                invalid(section, '項目ごとに入力してください。', 'INVALID_INPUT')
        for section in ('knowledge', 'faq', 'rates'):
            if not isinstance(reviewed.get(section, []), list) or not all(isinstance(item, dict) for item in reviewed.get(section, [])):
                invalid(section, '項目ごとに入力してください。', 'INVALID_INPUT')
        if fields:
            raise AppError(codes[0], '入力内容を確認してください。', field_errors=fields)
        prop = reviewed.get('property', {})
        meta = reviewed.get('document', {})
        scope = meta.get('scope', 'property')
        if not isinstance(scope, str) or scope not in {'general', 'company', 'property'}:
            invalid('document.scope', '資料の範囲を選択してください。', 'INVALID_KNOWLEDGE_SCOPE')
        if scope != 'property' and prop:
            invalid('document.scope', '共通・会社資料に物件情報は含められません。', 'SCOPE_PROPERTY_CONFLICT')
        for key in set(prop) - PROPERTY_KEYS:
            invalid(f'property.{key}', '物件情報に未対応の項目です。', 'INVALID_PROPERTY_FIELDS')
        labels = {'price': '価格', 'land_area': '土地面積', 'building_area': '建物面積', 'walking_minutes': '徒歩分数',
                  'property_name': '物件名', 'lot': '号地', 'address': '住所', 'station': '最寄駅', 'layout': '間取り',
                  'parking': '駐車場', 'completion_date': '完成年月', 'equipment': '設備情報', 'surroundings': '周辺環境'}
        numeric = {'price', 'land_area', 'building_area', 'walking_minutes'}
        for key, value in prop.items():
            if value is None: continue
            label = labels.get(key, '資料情報')
            if key in numeric:
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                    invalid(f'property.{key}', f'{label}は0以上の数値で入力してください。', 'INVALID_PROPERTY_VALUE')
            elif key in {'equipment', 'surroundings'}:
                if not isinstance(value, list) or len(value) > 100 or not all(isinstance(item, str) and len(item) <= 2000 for item in value):
                    invalid(f'property.{key}', f'{label}を項目ごとに入力してください。', 'INVALID_PROPERTY_VALUE')
            elif not isinstance(value, str) or len(value) > 2000:
                invalid(f'property.{key}', f'{label}を2000文字以内で入力してください。', 'INVALID_PROPERTY_VALUE')
        source_labels = {'source_url': '出典URL', 'source_name': '出典名', 'checked_at': '確認日', 'effective_date': '基準日', 'valid_until': '有効期限'}
        if scope != 'property':
            for key, label in source_labels.items():
                value = meta.get(key)
                if complete and (not isinstance(value, str) or not value.strip()):
                    invalid(f'document.{key}', f'{label}を入力してください。', 'KNOWLEDGE_SOURCE_REQUIRED')
                elif value is not None and not isinstance(value, str):
                    invalid(f'document.{key}', f'{label}を入力してください。', 'KNOWLEDGE_SOURCE_REQUIRED')
                elif key in {'checked_at', 'effective_date', 'valid_until'} and value:
                    try: date.fromisoformat(value)
                    except ValueError: invalid(f'document.{key}', f'{label}は YYYY-MM-DD で入力してください。', 'DOCUMENT_DATE_INVALID')
        for section in ('knowledge', 'faq', 'rates'):
            for i, item in enumerate(reviewed.get(section, [])):
                prefix = f'{section}.{i}'
                if 'reference' in item and not isinstance(item['reference'], dict):
                    invalid(f'{prefix}.reference', '出典情報を確認してください。', 'INVALID_INPUT')
                required = {'knowledge': {'text': '資料テキスト'}, 'faq': {'question': '質問', 'answer': '回答'},
                            'rates': {'bank': '金融機関', 'product': '商品名', 'rate_type': '金利タイプ', 'effective_date': '基準日',
                                      'valid_until': '有効期限', 'notes': '適用条件', 'source_url': '出典URL'}}[section]
                code = {'knowledge': 'INVALID_KNOWLEDGE', 'faq': 'INVALID_FAQ', 'rates': 'INVALID_RATE'}[section]
                for key, label in required.items():
                    value = item.get(key)
                    if complete and (not isinstance(value, str) or not value.strip()):
                        invalid(f'{prefix}.{key}', f'{"金利の" if section == "rates" else ""}{label}を入力してください。', code)
                    elif value is not None and not isinstance(value, str):
                        invalid(f'{prefix}.{key}', f'{label}を入力してください。', code)
                if section == 'knowledge' and isinstance(item.get('text'), str) and len(item['text']) > 30000:
                    invalid(f'{prefix}.text', '資料テキストは30000文字以内で入力してください。', code)
                if section == 'rates':
                    if 'conditions' in item and (not isinstance(item['conditions'], list) or not all(isinstance(v, str) and len(v) <= 2000 for v in item['conditions']) or len(item['conditions']) > 100):
                        invalid(f'{prefix}.conditions', '適用条件は項目ごとに2000文字以内で入力してください。', 'INVALID_RATE_CONDITIONS')
                    value = item.get('rate')
                    if (complete or value is not None) and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 20):
                        invalid(f'{prefix}.rate', '参考金利は0～20%で入力してください。', code)
                    alternate_rate = item.get('rate_over_90_percent')
                    if alternate_rate not in (None, '') and (not isinstance(alternate_rate, (int, float)) or isinstance(alternate_rate, bool) or not math.isfinite(alternate_rate) or not 0 <= alternate_rate <= 20):
                        invalid(f'{prefix}.rate_over_90_percent', '融資率9割超の参考金利は0～20%で入力してください。', code)
                    boundaries = {}
                    for key, label in (('years_min', '返済期間の下限'), ('years_max', '返済期間の上限'),
                                       ('loan_amount_min', '借入額の下限'), ('loan_amount_max', '借入額の上限'),
                                       ('max_loan_to_value', '融資率の上限')):
                        value = item.get(key)
                        if value in (None, ''): continue
                        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                            invalid(f'{prefix}.{key}', f'{label}は0より大きい数値で入力してください。', 'INVALID_RATE_CONDITIONS')
                        elif key.startswith('years_') and (not float(value).is_integer() or not 1 <= value <= 50):
                            invalid(f'{prefix}.{key}', f'{label}は1～50年の整数で入力してください。', 'INVALID_RATE_CONDITIONS')
                        else:
                            boundaries[key] = value
                    for lower, upper, label in (('years_min', 'years_max', '返済期間'), ('loan_amount_min', 'loan_amount_max', '借入額')):
                        if lower in boundaries and upper in boundaries and boundaries[lower] > boundaries[upper]:
                            invalid(f'{prefix}.{upper}', f'{label}の上限は下限以上で入力してください。', 'INVALID_RATE_CONDITIONS')
                    parsed_dates = {}
                    for key, label in (('effective_date', '基準日'), ('valid_until', '有効期限')):
                        value = item.get(key)
                        if isinstance(value, str) and value:
                            try: parsed_dates[key] = date.fromisoformat(value)
                            except ValueError: invalid(f'{prefix}.{key}', f'金利の{label}は YYYY-MM-DD で入力してください。', 'INVALID_RATE_DATE')
                    if len(parsed_dates) == 2 and parsed_dates['effective_date'] > parsed_dates['valid_until']:
                        invalid(f'{prefix}.valid_until', '金利の有効期限は基準日以降の日付を入力してください。', 'INVALID_RATE_DATE')
        if fields:
            raise AppError(codes[0], '入力内容を確認してください。', field_errors=fields)

    def validate_review(self, reviewed, record):
        self._validate_form_fields(reviewed, complete=True)
        meta=reviewed.get('document', {})
        scope=meta.get('scope','property')
        if scope not in {'general','company','property'}: raise AppError('INVALID_KNOWLEDGE_SCOPE','資料範囲を general / company / property で確認してください。')
        if scope!='property':
            if reviewed.get('property'): raise AppError('SCOPE_PROPERTY_CONFLICT','共通・会社資料へ物件情報を混在させないでください。')
            for key in ('source_url','source_name','checked_at','effective_date','valid_until'):
                if not isinstance(meta.get(key),str) or not meta[key].strip(): raise AppError('KNOWLEDGE_SOURCE_REQUIRED',f'{key} を確認してください。')
            for key in ('checked_at','effective_date','valid_until'):
                try: date.fromisoformat(meta[key])
                except ValueError: raise AppError('DOCUMENT_DATE_INVALID','資料日付は YYYY-MM-DD です。')
        if set(reviewed.get('property', {})) - PROPERTY_KEYS:
            raise AppError('INVALID_PROPERTY_FIELDS', '物件情報に未対応の項目があります。')
        numeric_keys = {'price', 'land_area', 'building_area', 'walking_minutes'}
        for key, value in reviewed['property'].items():
            if value is None:
                continue
            if key in {'equipment', 'surroundings'}:
                if not isinstance(value, list) or not all(isinstance(v, str) and len(v) <= 2000 for v in value) or len(value) > 100:
                    raise AppError('INVALID_PROPERTY_VALUE', f'{key} は文字列の配列で入力してください。')
            elif key not in numeric_keys and (not isinstance(value, str) or len(value) > 2000):
                raise AppError('INVALID_PROPERTY_VALUE', f'{key} は文字列で入力してください。')
        for key in {'price', 'land_area', 'building_area', 'walking_minutes'}:
            value = reviewed['property'].get(key)
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0):
                raise AppError('INVALID_PROPERTY_VALUE', f'{key} の数値を確認してください。')
        ref = {'document_id': record['id'], 'filename': record['filename']}
        for section in ['knowledge', 'faq', 'rates']:
            for i, item in enumerate(reviewed.get(section, [])):
                if section == 'knowledge' and (not isinstance(item.get('text'), str) or not item['text'].strip() or len(item['text']) > 30000):
                    raise AppError('INVALID_KNOWLEDGE', '資料テキストを確認してください。')
                if section == 'faq' and not all(isinstance(item.get(k), str) and item[k].strip() for k in ['question', 'answer']):
                    raise AppError('INVALID_FAQ', 'FAQ の質問と回答を入力してください。')
                location = str(item.get('reference', {}).get('location', '管理者確認'))[:100]
                item['reference'] = dict(item.get('reference', {}), **ref, location=location, source_url=item.get('source_url', meta.get('source_url', reviewed['property'].get('source_url', ''))))
                if section == 'rates':
                    item['id'] = f"{record['id']}:rate:{i}"
                    for key in ['bank', 'product', 'rate_type', 'effective_date', 'valid_until', 'notes', 'source_url']:
                        if not isinstance(item.get(key), str) or not item[key].strip():
                            raise AppError('INVALID_RATE', f'金利の {key} が必要です。')
                    if not isinstance(item.get('rate'), (int, float)) or not math.isfinite(item['rate']) or not 0 <= item['rate'] <= 20:
                        raise AppError('INVALID_RATE', '参考金利は0～20%で入力してください。')
                    try:
                        if date.fromisoformat(str(item['effective_date'])) > date.fromisoformat(str(item['valid_until'])):
                            raise ValueError()
                    except ValueError:
                        raise AppError('INVALID_RATE_DATE', '金利の有効期間を YYYY-MM-DD で入力してください。')
        return reviewed

    def publish(self, ids):
        from app.services.publications import PublicationService
        service = PublicationService(self.store, self)
        draft = service.create()
        items = [{'document_id': id, 'confirmation_id': self.store.get('documents', id).get('confirmation_id')} for id in ids]
        draft = service.save(draft['id'], draft['revision'], items, '確認済み資料の公開')
        preview = service.preview(draft['id'])
        return service.publish(draft['id'], draft['revision'], preview['preview_token'], uuid.uuid4().hex)
