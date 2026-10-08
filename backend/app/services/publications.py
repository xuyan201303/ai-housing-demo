"""Employee publication drafts with immutable approval identities and atomic commit."""
import copy
import hashlib
import json
import re
from decimal import Decimal
import uuid
from datetime import date
from app.models.domain import AppError, now


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class PublicationService:
    def __init__(self, store, documents):
        self.store, self.documents = store, documents

    @staticmethod
    def _latest(db):
        row = db.execute('SELECT version,payload FROM versions ORDER BY version DESC LIMIT 1').fetchone()
        return dict(json.loads(row['payload']), version=row['version']) if row else {'version': None, 'document_ids': [], 'document_approvals': {}}

    @staticmethod
    def _entries(version):
        return [{'document_id': id, 'confirmation_id': version.get('document_approvals', {}).get(id)} for id in version.get('document_ids', [])]

    def _read(self, db, id):
        row = db.execute('SELECT payload FROM publication_drafts WHERE id=?', (id,)).fetchone()
        if not row: raise AppError('DRAFT_NOT_FOUND', '公開草案が見つかりません。', 404)
        return json.loads(row['payload'])

    @staticmethod
    def _write(db, draft):
        db.execute('INSERT INTO publication_drafts VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (draft['id'], json.dumps(draft, ensure_ascii=False)))

    def _summary(self, db, item):
        row = db.execute('SELECT payload FROM documents WHERE id=?', (item['document_id'],)).fetchone()
        record = json.loads(row['payload']) if row else {}
        revrow = db.execute('SELECT id,payload FROM document_revisions WHERE confirmation_id=? AND document_id=?', (item.get('confirmation_id'), item['document_id'])).fetchone()
        proofrow = db.execute('SELECT payload FROM confirmations WHERE id=? AND document_id=?', (item.get('confirmation_id'), item['document_id'])).fetchone()
        proof = json.loads(proofrow['payload']) if proofrow else {}
        return dict(item, filename=record.get('filename', '資料が見つかりません'), revision_id=revrow['id'] if revrow else None,
                    usage=proof.get('usage', 'unclassified'), scope=proof.get('reviewed', {}).get('document', {}).get('scope', 'property'),
                    confirmed_at=proof.get('confirmed_at'))

    def _view(self, db, draft):
        result = copy.deepcopy(draft)
        result['items'] = [self._summary(db, item) for item in draft['items']]
        return result

    def list(self):
        with self.store.connect() as db:
            return [self._view(db, json.loads(row['payload'])) for row in db.execute('SELECT payload FROM publication_drafts ORDER BY rowid DESC')]

    def get(self, id):
        with self.store.connect() as db: return self._view(db, self._read(db, id))

    def create(self, restore_version=None, actor='admin'):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); current = self._latest(db); source = current
            if restore_version is not None:
                row = db.execute('SELECT payload FROM versions WHERE version=?', (restore_version,)).fetchone()
                if not row: raise AppError('VERSION_NOT_FOUND', '復元する公開版が見つかりません。', 404)
                source = json.loads(row['payload'])
            draft = {'id': uuid.uuid4().hex, 'revision': 0, 'base_version': current['version'], 'items': self._entries(source),
                     'note': '', 'state': 'open', 'created_at': now(), 'created_by': actor, 'saved_at': now(),
                     'restore_version': restore_version, 'preview_token': None}
            self._write(db, draft)
            return self._view(db, draft)

    def save(self, id, revision, items, note, actor='admin'):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); draft = self._read(db, id)
            self._require_open(draft, revision)
            if len(items) > 100 or len({i['document_id'] for i in items}) != len(items):
                raise AppError('DUPLICATE_DOCUMENT', '同じ資料を重複して選択できません。')
            # Preserve explicit identity relations; never infer replacements by filename.
            baseline = self._entries(self._version(db, draft['base_version']))
            for item in items:
                if item.get('replaces_document_id'):
                    target = next((v for v in baseline if v['document_id'] == item['replaces_document_id']), None)
                    row = db.execute('SELECT payload FROM documents WHERE id=?', (item['document_id'],)).fetchone()
                    record = json.loads(row['payload']) if row else {}
                    if record.get('replaces_document_id') and (record['replaces_document_id'] != item['replaces_document_id'] or record.get('replaces_confirmation_id') != item.get('replaces_confirmation_id')):
                        raise AppError('REPLACEMENT_MISMATCH', 'アップロード時の差し替え対象と一致しません。新しい対象で更新を準備してください。', 409)
                    if not target or target['confirmation_id'] != item.get('replaces_confirmation_id'):
                        raise AppError('REPLACEMENT_MISMATCH', '差し替え対象の資料・確認修訂が公開基線と一致しません。', 409)
                    if item['replaces_document_id'] in {v['document_id'] for v in items} and item['replaces_document_id'] != item['document_id']:
                        raise AppError('REPLACEMENT_CONFLICT', '差し替え元の資料も残っています。置き換える対象を確認してください。', 409)
            targets = [i['replaces_document_id'] for i in items if i.get('replaces_document_id')]
            if len(targets) != len(set(targets)): raise AppError('REPLACEMENT_CONFLICT', '同じ資料を複数の資料で置き換えることはできません。', 409)
            draft.update(items=copy.deepcopy(items), note=note, revision=revision + 1, saved_at=now(), saved_by=actor,
                         preview_token=None, preview_digest=None)
            self._write(db, draft); return self._view(db, draft)

    @staticmethod
    def _require_open(draft, revision):
        if draft['state'] != 'open': raise AppError('PUBLICATION_DRAFT_CLOSED', 'この公開草案はすでに公開されています。', 409)
        if draft['revision'] != revision: raise AppError('PUBLICATION_DRAFT_CONFLICT', '別の画面で草案が更新されました。再度開いて変更内容を確認してください。', 409)

    @staticmethod
    def _version(db, version):
        if version is None: return {'document_ids': [], 'document_approvals': {}}
        row = db.execute('SELECT payload FROM versions WHERE version=?', (version,)).fetchone()
        if not row: raise AppError('VERSION_NOT_FOUND', '公開基線が見つかりません。', 409)
        return json.loads(row['payload'])

    def _state_digest(self, db, draft):
        identities = {i['document_id'] for i in draft['items']}
        identities.update(i['document_id'] for i in self._entries(self._version(db, draft['base_version'])))
        docs = []
        for id in sorted(identities):
            row = db.execute('SELECT payload FROM documents WHERE id=?', (id,)).fetchone()
            # Draft and raw are not release facts. Permission/latest approval changes are relevant.
            record = json.loads(row['payload']) if row else None
            docs.append((id, {k: record.get(k) for k in ('sha256', 'status', 'usage', 'usage_epoch', 'usage_changed_at', 'confirmation_id')} if record else None))
        proofs = []
        for item in draft['items']:
            row = db.execute('SELECT payload FROM confirmations WHERE id=? AND document_id=?', (item.get('confirmation_id'), item['document_id'])).fetchone()
            rev = db.execute('SELECT payload FROM document_revisions WHERE confirmation_id=? AND document_id=?', (item.get('confirmation_id'), item['document_id'])).fetchone()
            proofs.append((item, row['payload'] if row else None, rev['payload'] if rev else None))
        return digest({'base': self._latest(db)['version'], 'draft_revision': draft['revision'], 'items': draft['items'], 'note': draft['note'],
                       'documents': docs, 'proofs': proofs, 'today': now()[:10]})

    def _proof(self, db, item):
        id, cid = item['document_id'], item.get('confirmation_id')
        row = db.execute('SELECT payload FROM documents WHERE id=?', (id,)).fetchone()
        if not row: raise AppError('NOT_FOUND', '資料が見つかりません。', 409)
        record = json.loads(row['payload'])
        if record.get('update_cancelled'): raise AppError('CANCELLED_UPDATE', 'この更新は取り消されています。更新を再開して内容を確認してください。', 409)
        if record.get('status') not in {'confirmed', 'published'}: raise AppError('UNCONFIRMED_DOCUMENT', '確認済みの資料のみ公開できます。資料の利用権限・内容を再確認してください。', 409)
        if record.get('usage') != 'customer': raise AppError('CUSTOMER_USAGE_REQUIRED', '顧客への案内に使用可ではありません。資料用途を確認してください。', 409)
        if not isinstance(cid, int) or isinstance(cid, bool): raise AppError('UNCONFIRMED_DOCUMENT', '確認修訂を選択してください。', 409)
        row = db.execute('SELECT payload FROM confirmations WHERE id=? AND document_id=?', (cid, id)).fetchone()
        if not row: raise AppError('CONFIRMATION_MISMATCH', '資料と確認修訂の組み合わせが一致しません。', 409)
        proof = json.loads(row['payload'])
        if proof.get('event') != 'business_confirmation' or proof.get('usage') != 'customer' or not proof.get('actor') or not proof.get('confirmed_at'):
            raise AppError('CUSTOMER_USAGE_REQUIRED', '顧客への案内に使用可として内容を確認してください。', 409)
        rev = db.execute('SELECT payload FROM document_revisions WHERE confirmation_id=? AND document_id=?', (cid, id)).fetchone()
        if rev:
            assoc = json.loads(rev['payload'])
            if assoc.get('cancelled'): raise AppError('CANCELLED_REVISION', 'この未公開修訂は取り消されています。新しい修訂を準備してください。', 409)
            if assoc.get('usage_epoch', 0) != record.get('usage_epoch', 0): raise AppError('REVOKED_APPROVAL', 'この確認は資料用途の変更で撤回されています。現在の資料を改めて確認してください。', 409)
        elif (record.get('confirmation_id') != cid or proof.get('usage_epoch', 0) != record.get('usage_epoch', 0) or
              (record.get('usage_changed_at') and record['usage_changed_at'] > proof['confirmed_at'])):
            raise AppError('REVOKED_APPROVAL', 'この確認の利用根拠が失われています。現在の資料を改めて確認してください。', 409)
        return record, proof

    def _compose(self, db, draft):
        snapshot = {'published_at': now(), 'property': {}, 'knowledge': [], 'rates': [], 'faq': [], 'references': [],
                    'document_ids': [], 'document_approvals': {}, 'document_revisions': {}, 'document_validity': {}}
        blockers = []; records = []; today = date.fromisoformat(now()[:10]); hashes = set()
        for item in draft['items']:
            try:
                record, proof = self._proof(db, item); review = proof['reviewed']; id = item['document_id']
                if record['filename'].lower().startswith('minimal.') or 'smoke' in json.dumps(record.get('normalized'), ensure_ascii=False).lower():
                    raise AppError('TEST_FIXTURE', 'SDK smoke 用資料は公開できません。')
                # Narrow, deterministic check for the SDK's existing key:value
                # price format. Do not rewrite evidence or infer free-text facts.
                price = review.get('property', {}).get('price')
                literal_prices = {Decimal(match) for item in review.get('knowledge', [])
                                  for match in re.findall(r'(?m)^\s*price\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*$', str(item.get('text', '')))}
                if price is not None and len(literal_prices) == 1 and Decimal(str(price)) not in literal_prices:
                    raise AppError('SOURCE_PRICE_CONFLICT', '資料本文の価格と登録価格が一致しません。本文を確認するか、更新したファイルに差し替えてください。', 409)
                scope = review.get('document', {}).get('scope', 'property'); meta = review.get('property', {}) if scope == 'property' else review.get('document', {})
                if review.get('property') or any(review.get(k) for k in ('knowledge', 'faq', 'rates')):
                    try: end = date.fromisoformat(str(meta['valid_until'])[:10])
                    except (KeyError, TypeError, ValueError): raise AppError('DOCUMENT_VALIDITY_REQUIRED', '資料の有効期限を確認してください。', 409)
                    if end < today: raise AppError('DOCUMENT_EXPIRED', '資料の有効期限が過ぎています。新しい資料を確認してください。', 409)
                    if meta.get('effective_date'):
                        try: start = date.fromisoformat(str(meta['effective_date'])[:10])
                        except ValueError: raise AppError('DOCUMENT_DATE_INVALID', '資料の基準日を確認してください。', 409)
                        if start > today: raise AppError('DOCUMENT_NOT_YET_EFFECTIVE', '基準日が未来のため、まだ公開できません。', 409)
                    snapshot['document_validity'][id] = {'valid_until': end.isoformat(), 'effective_date': meta.get('effective_date'), 'filename': record['filename'], 'scope': scope}
                for rate in review.get('rates', []):
                    try:
                        if not date.fromisoformat(rate['effective_date'][:10]) <= today <= date.fromisoformat(rate['valid_until'][:10]):
                            raise AppError('RATE_EXPIRED', '商品金利の期間外です。基準日と有効期限を確認してください。', 409)
                    except (KeyError, TypeError, ValueError): raise AppError('INVALID_RATE_DATE', '商品金利の日付を確認してください。', 409)
                for key, value in review.get('property', {}).items():
                    prior = snapshot['property'].get(key)
                    if prior is not None and prior != value and key not in {'source_url', 'source_name', 'checked_at', 'effective_date', 'valid_until', 'scope_notes'}:
                        if key in {'equipment', 'surroundings'} and isinstance(prior, list) and isinstance(value, list): value = list(dict.fromkeys(prior + value))
                        else: raise AppError('CONFLICTING_PROPERTY', f'物件の{key}が他の資料と異なります。差し替え対象と値を確認してください。', 409)
                    snapshot['property'][key] = value
                for section in ('knowledge', 'rates', 'faq'): snapshot[section].extend([dict(i, scope=scope) for i in review.get(section, [])])
                snapshot['document_ids'].append(id); snapshot['document_approvals'][id] = item['confirmation_id']
                rev = db.execute('SELECT id FROM document_revisions WHERE confirmation_id=? AND document_id=?', (item['confirmation_id'], id)).fetchone()
                snapshot['document_revisions'][id] = rev['id'] if rev else None
                snapshot['references'].append({'document_id': id, 'filename': record['filename'], 'location': '管理者確認・公開済み', 'source_url': meta.get('source_url', '')})
                records.append((record, review))
            except AppError as exc:
                blockers.append({'code': exc.code, 'message': f"{self._summary(db, item)['filename']}：{exc.message}", 'document_id': item['document_id']})
        if snapshot['property'] and any(not snapshot['property'].get(k) for k in ('property_name', 'lot', 'price')):
            blockers.append({'code': 'PROPERTY_REQUIRED', 'message': '物件名・号地・価格がそろっていません。物件概要を追加するか、不完全な物件資料を外してください。'})
        # An empty release is a useful, explicit withdrawal; absent abilities are warnings.
        dates = [v['valid_until'] for v in snapshot['document_validity'].values() if v['scope'] == 'property']
        if dates and snapshot['property']: snapshot['property']['valid_until'] = min(dates)
        if snapshot['property']: snapshot['property']['field_references'] = {k: {'document_id': r['id'], 'filename': r['filename'], 'location': '管理者確認・公開済み'} for r, review in records for k in review.get('property', {})}
        capabilities = {'property': bool(snapshot['property']), 'equipment': bool(snapshot['property'].get('equipment')), 'faq': bool(snapshot['faq'] or snapshot['knowledge']), 'mortgage': bool(snapshot['rates'])}
        warnings = [{'code': code, 'message': message} for key, code, message in (
            ('property', 'NO_PROPERTY', '物件紹介・物件価格の案内が利用できません。'),
            ('equipment', 'NO_EQUIPMENT', '登録済み設備の案内が利用できません。'),
            ('faq', 'NO_GENERAL_KNOWLEDGE', '登録資料に基づく一般相談の回答範囲がありません。'),
            ('mortgage', 'NO_RATES', '登録金利を使った住宅ローン試算が利用できません。')) if not capabilities[key]]
        return snapshot, blockers, warnings, capabilities

    def _diff(self, db, draft, candidate=None):
        baseline_snapshot = self._version(db, draft['base_version'])
        candidate = candidate if candidate is not None else self._compose(db, draft)[0]
        base = self._entries(baseline_snapshot); byid = {i['document_id']: i for i in base}
        added = []; retained = []; replaced = []; consumed = set(); changes = []
        labels = {'price': '価格', 'equipment': '設備', 'surroundings': '周辺環境', 'property_name': '物件名', 'lot': '号地', 'address': '住所',
                  'layout': '間取り', 'land_area': '土地面積', 'building_area': '建物面積', 'station': '最寄駅', 'walking_minutes': '徒歩分数',
                  'completion_date': '完成年月', 'parking': '駐車場', 'faq': 'FAQ', 'rates': '金利・適用条件・借入条件',
                  'effective_date': '基準日', 'valid_until': '有効期限', 'scope': '資料範囲', 'usage': '資料用途', 'knowledge': '資料本文・一般相談の根拠'}
        def values(item):
            row = db.execute('SELECT payload FROM confirmations WHERE id=? AND document_id=?', (item.get('confirmation_id'), item['document_id'])).fetchone()
            proof = json.loads(row['payload']) if row else {}; review = proof.get('reviewed', {})
            meta = review.get('document', {}) if review.get('document', {}).get('scope', 'property') != 'property' else review.get('property', {})
            result = {k: v for k, v in review.get('property', {}).items() if k in labels}
            result.update({k: meta.get(k) for k in ('effective_date', 'valid_until')}); result.update(scope=review.get('document', {}).get('scope', 'property'), usage=proof.get('usage'), faq=review.get('faq', []), knowledge=[{'text': item.get('text', '')} for item in review.get('knowledge', [])])
            keys = ('bank', 'product', 'rate_type', 'rate', 'notes', 'conditions', 'years_min', 'years_max', 'loan_amount_min', 'loan_amount_max', 'max_loan_to_value', 'rate_over_90_percent', 'effective_date', 'valid_until')
            result['rates'] = [{k: r.get(k) for k in keys if k in r} for r in review.get('rates', [])]
            return result
        for item in draft['items']:
            id = item['document_id']; old = byid.get(id)
            if not old:
                targetid = item.get('replaces_document_id')
                if targetid in byid and targetid not in {i['document_id'] for i in draft['items']}: old = byid[targetid]
            if old:
                consumed.add(old['document_id'])
                if old['document_id'] == id and old['confirmation_id'] == item['confirmation_id']: retained.append(self._summary(db, item)); continue
                replaced.append({'before': self._summary(db, old), 'after': self._summary(db, item)})
                before, after = values(old), values(item)
                for key in labels:
                    if before.get(key) != after.get(key): changes.append({'document_id': id, 'label': labels[key], 'before': before.get(key), 'after': after.get(key)})
            else: added.append(self._summary(db, item))
        removed = [self._summary(db, i) for i in base if i['document_id'] not in consumed and i['document_id'] not in {v['document_id'] for v in draft['items']}]
        # A restore can add one file and remove another without an explicit
        # replacement relation. Compare the resulting business content as well
        # as source identities, so its actual price/ability change remains visible.
        rate_keys = ('bank', 'product', 'rate_type', 'rate', 'notes', 'conditions', 'years_min', 'years_max',
                     'loan_amount_min', 'loan_amount_max', 'max_loan_to_value', 'rate_over_90_percent', 'effective_date', 'valid_until')
        def business(snapshot, entries):
            prop = snapshot.get('property', {})
            result = {key: prop.get(key) for key in labels if key not in {'faq', 'rates', 'scope', 'usage', 'knowledge'}}
            result['faq'] = [{key: item.get(key) for key in ('question', 'answer')} for item in snapshot.get('faq', [])]
            result['rates'] = [{key: item[key] for key in rate_keys if key in item} for item in snapshot.get('rates', [])]
            result['knowledge'] = [{'text': item.get('text', '')} for item in snapshot.get('knowledge', [])]
            summaries = [self._summary(db, item) for item in entries]
            result['usage'] = sorted({item['usage'] for item in summaries})
            result['scope'] = sorted({item['scope'] for item in summaries})
            return result
        before_business = business(baseline_snapshot, base)
        after_business = business(candidate, draft['items'])
        for key, label in labels.items():
            before, after = before_business.get(key), after_business.get(key)
            if before != after and not any(c['label'] == label and c['before'] == before and c['after'] == after for c in changes):
                changes.append({'document_id': None, 'label': label, 'before': before, 'after': after, 'level': 'publication'})
        return {'added': added, 'retained': retained, 'replaced': replaced, 'removed': removed, 'changes': changes}

    def preview(self, id):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); draft = self._read(db, id); self._require_open(draft, draft['revision'])
            snapshot, blockers, warnings, capabilities = self._compose(db, draft)
            if self._latest(db)['version'] != draft['base_version']:
                blockers.insert(0, {'code': 'PUBLICATION_BASE_CHANGED', 'message': '現在の公開版が変わりました。新しい公開版から草案を作り直してください。'})
            token = uuid.uuid4().hex; stamp = self._state_digest(db, draft)
            draft.update(preview_token=token, preview_digest=stamp, previewed_at=now()); self._write(db, draft)
            return dict(self._diff(db, draft, snapshot), draft_id=id, draft_revision=draft['revision'], base_version=draft['base_version'],
                        preview_token=token, blockers=blockers, warnings=warnings, capabilities=capabilities, items=[self._summary(db, i) for i in draft['items']])

    def publish(self, id, revision, preview_token, idempotency_key, actor='admin'):
        request_digest = digest([id, revision, preview_token])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            receipt = db.execute('SELECT * FROM publication_submissions WHERE idempotency_key=?', (idempotency_key,)).fetchone()
            if receipt:
                if receipt['draft_id'] != id or receipt['request_digest'] != request_digest: raise AppError('IDEMPOTENCY_CONFLICT', '同じ送信識別子が別の公開操作に使われています。', 409)
                row = db.execute('SELECT payload FROM versions WHERE version=?', (receipt['version'],)).fetchone()
                return dict(json.loads(row['payload']), version=receipt['version'], replayed=True)
            draft = self._read(db, id); self._require_open(draft, revision)
            if self._latest(db)['version'] != draft['base_version']: raise AppError('PUBLICATION_BASE_CHANGED', '公開基線が更新されました。現在の公開版から草案を作り直してください。', 409)
            if not preview_token or preview_token != draft.get('preview_token') or self._state_digest(db, draft) != draft.get('preview_digest'):
                raise AppError('PUBLICATION_PREVIEW_STALE', '資料・確認・草案の状態が変わりました。変更内容をもう一度プレビューしてください。', 409)
            snapshot, blockers, warnings, capabilities = self._compose(db, draft)
            if blockers: raise AppError(blockers[0]['code'], blockers[0]['message'], 409)
            if not draft['note'].strip(): raise AppError('PUBLICATION_NOTE_REQUIRED', '公開する変更の説明を入力してください。', field_errors={'note': '変更の説明を入力してください。'})
            snapshot.update(published_by=actor, actor_label='共有管理者 (admin)' if actor == 'admin' else actor,
                            change_note=draft['note'], base_version=draft['base_version'], restore_version=draft.get('restore_version'),
                            publication_draft_id=id, capabilities=capabilities, publication_diff=self._diff(db, draft, snapshot))
            cursor = db.execute('INSERT INTO versions(payload) VALUES (?)', (json.dumps(snapshot, ensure_ascii=False),)); version = cursor.lastrowid
            for docid in snapshot['document_ids']:
                row = db.execute('SELECT payload FROM documents WHERE id=?', (docid,)).fetchone(); record = json.loads(row['payload'])
                record.update(status='published', published_version=version)
                db.execute('UPDATE documents SET payload=? WHERE id=?', (json.dumps(record, ensure_ascii=False), docid))
            draft.update(state='published', published_version=version, published_at=snapshot['published_at'], published_by=actor)
            self._write(db, draft)
            db.execute('INSERT INTO publication_submissions VALUES (?,?,?,?)', (idempotency_key, id, request_digest, version))
            return dict(snapshot, version=version)
