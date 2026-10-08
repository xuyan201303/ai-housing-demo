"""Fail-closed Customer projections of existing internal data; never mutate it.

This is a field boundary, not a confidentiality classifier for allowed prose.
"""
import math
import re
from datetime import date
from urllib.parse import urlsplit
from app.models.domain import AppError, now
from app.services.context import snapshot_for, selected, validate_property
from app.schemas.customer import (
    CustomerSource, CustomerProperty, CustomerCandidate, CustomerProduct,
    CustomerMortgage, CustomerHit, PropertyDisplay, CandidatesDisplay, SourcesDisplay,
    ProductsDisplay, MortgageDisplay, CustomerMessage, CustomerStaffCall,
    CustomerRealtime, CustomerVoiceError, CustomerSession, CustomerSessionCreated, CustomerAnswer,
)


# Explicit reviewed public source pages from research/SOURCE_MANIFEST.md.
# New origins/paths are NOT automatically approved, even on these domains.
PUBLIC_SOURCE_URLS = frozenset({
    'https://www.mlit.go.jp/totikensangyo/const/1_6_bf_000013.html',
    'https://www.flat35.com/loan/lineup/flat35/index.html',
    'https://www.flat35.com/loan/lineup/flat35/flow_shinchiku.html',
    'https://www.flat35.com/loan/lineup/flat35/conditions/index.html',
    'https://www.bk.mufg.jp/kariru/jutaku/yuuguu/index.html',
    'https://www.simulation.jhf.go.jp/flat35/kinri/index.php/rates/top',
    *('https://www.sekisuihouse.co.jp/bunjou/1/12221/b350007/s357006/00015123/' + page
      for page in ('06top.html', '06gaiyou.html', '06town.html')),
})
SOURCE_LABELS = {'property': '確認・公開済み物件資料', 'general': '確認・公開済み住宅購入資料',
                 'company': '確認・公開済み会社資料', 'rate': '確認・公開済み参考金利資料'}


def obj(value):
    return value if isinstance(value, dict) else {}


def text(value):
    return value if isinstance(value, str) else None


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def strings(value):
    if isinstance(value, str): return [value]
    return [s for s in value if isinstance(s, str)] if isinstance(value, list) else []


def public_url(value):
    if not isinstance(value, str) or value not in PUBLIC_SOURCE_URLS: return None
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
        return None
    return value


def current(value):
    try:
        return date.fromisoformat(value['effective_date'][:10]) <= date.fromisoformat(now()[:10]) <= date.fromisoformat(value['valid_until'][:10])
    except (KeyError, TypeError, ValueError):
        return False


def source(ref, scope='property'):
    return CustomerSource(label=SOURCE_LABELS.get(scope, SOURCE_LABELS['property']), url=public_url(obj(ref).get('source_url')))


def sources(refs, snapshot, scope=None):
    values = []
    for ref in refs if isinstance(refs, list) else []:
        ref = obj(ref)
        if ref.get('document_id') not in snapshot.get('document_ids', []): continue
        ref_scope = scope or obj(snapshot.get('document_validity', {})).get(ref.get('document_id'), {}).get('scope', 'property')
        value = source(ref, ref_scope)
        if value not in values: values.append(value)
    return values


def property_view(session, snapshot):
    target = selected(session, snapshot)
    if not target: return None
    try:
        validate_property(snapshot, target, date.fromisoformat(now()[:10]))
    except AppError:
        return None
    p = obj(snapshot.get('property'))
    scalar = {k: text(p.get(k)) for k in ('lot', 'address', 'layout', 'station', 'completion_date', 'parking',
                                         'checked_at', 'effective_date', 'valid_until')}
    amounts = {k: number(p.get(k)) for k in ('price', 'walking_minutes', 'land_area', 'building_area')}
    # Do not expose admin-entered scope_notes. Retain known business limitation
    # through deterministic application copy, never AI rewriting/classification.
    notices = []
    if text(p.get('scope_notes')):
        notices.append('交通・徒歩距離の対象範囲をご確認ください。分譲全体の範囲として記載された値を、号地単独の正確な距離として扱わないでください。')
    refs = [r for r in snapshot.get('references', []) if obj(snapshot.get('document_validity', {})).get(obj(r).get('document_id'), {}).get('scope', 'property') == 'property']
    return CustomerProperty(property_id=target, property_name=text(p.get('property_name')) or '公開物件',
                            equipment=strings(p.get('equipment')), surroundings=strings(p.get('surroundings')),
                            scope_notices=notices, references=sources(refs, snapshot, 'property'), **scalar, **amounts)


def candidates(snapshot):
    p = obj(snapshot.get('property'))
    target = text(p.get('lot'))
    try:
        validate_property(snapshot, target, date.fromisoformat(now()[:10]))
    except AppError:
        return []
    return [CustomerCandidate(property_id=target, property_name=text(p.get('property_name')) or '公開物件')]


def products(snapshot):
    result = []
    for raw in snapshot.get('rates', []):
        r = obj(raw)
        if not current(r) or not all(text(r.get(k)) for k in ('id', 'product', 'rate_type')) or number(r.get('rate')) is None:
            continue
        result.append(CustomerProduct(
            **{k: r[k] for k in ('id', 'product', 'rate_type', 'effective_date', 'valid_until')}, bank=text(r.get('bank')) or '金融機関',
            **{k: number(r.get(k)) for k in ('rate', 'rate_over_90_percent', 'years_min', 'years_max', 'loan_amount_min', 'loan_amount_max', 'max_loan_to_value')},
            notes=text(r.get('notes')) or '', conditions=strings(r.get('conditions')),
            requires_acquisition_price_for_estimate=('rate_over_90_percent' in r or r.get('max_loan_to_value') not in (None, '') or 'フラット35' in r['product']),
            references=[source(r.get('reference'), 'rate')],
        ))
    return result


def mortgage_view(raw, snapshot):
    r = obj(raw)
    # A result must belong to this pinned published version and a current product.
    if r.get('version') != snapshot.get('version') or not current(r): return None
    if not any(p.id == r.get('rate_id') for p in products(snapshot)): return None
    if any(number(r.get(k)) is None for k in ('loan_amount', 'annual_interest_rate', 'years', 'monthly_payment')):
        return None
    rate = next(i for i in snapshot['rates'] if i['id'] == r['rate_id'])
    from app.services.mortgage import CALCULATION_NOTES
    return CustomerMortgage(
        version=r['version'], rate_id=r['rate_id'], calculation_date=text(r.get('calculation_date')) or '',
        effective_date=r['effective_date'], valid_until=r['valid_until'],
        **{k: number(r.get(k)) for k in ('property_price', 'down_payment', 'loan_amount', 'annual_interest_rate', 'years', 'monthly_payment', 'loan_to_value', 'loan_to_value_percent')},
        **{k: text(rate.get(k)) for k in ('bank', 'product', 'rate_type')},
        rate_basis=r.get('rate_basis') if r.get('rate_basis') in {'公開済み参考金利', '融資率9割超の公開済み参考金利', '融資率9割以下の公開済み参考金利'} else None,
        price_basis=r.get('price_basis') if r.get('price_basis') in {'物件未選択・顧客申告借入額', '顧客申告取得価格（物件資料との照合未実施）'} else None,
        notes=CALCULATION_NOTES + ' ' + (text(rate.get('notes')) or ''), product_notes=text(rate.get('notes')) or '',
        conditions=strings(rate.get('conditions')), references=sources(r.get('references'), snapshot),
    )


def staff_view(raw):
    r = obj(raw)
    status = r['status']
    prompts = {'pending': 'スタッフへの呼出を受け付けました。確認をお待ちください。',
               'accepted': 'スタッフが確認しました。ご案内まで少々お待ちください。',
               'completed': 'スタッフの対応が完了しました。'}
    return CustomerStaffCall(id=r['id'], status=status, customer_message=prompts[status],
                             **{k: text(r.get(k)) for k in ('created_at', 'accepted_at', 'completed_at')})


def hits(raw, session, snapshot, query=''):
    result = []
    for item in raw if isinstance(raw, list) else []:
        item = obj(item); scope = item.get('scope', 'property'); ref = obj(item.get('reference'))
        if scope not in {'general', 'company', 'property'}: continue
        if ref.get('document_id') not in snapshot.get('document_ids', []): continue
        allowed = snapshot.get('knowledge', []) + [dict(text=f"{i['question']}\n{i['answer']}", reference=i['reference'], scope=i.get('scope', 'property')) for i in snapshot.get('faq', [])]
        if not any(i.get('text') == item.get('text') and i.get('scope', 'property') == scope and obj(i.get('reference')).get('document_id') == ref.get('document_id') for i in allowed): continue
        if scope == 'property':
            if property_view(session, snapshot) is None: continue
        elif not current(obj(snapshot.get('document_validity')).get(ref.get('document_id'), {})):
            continue
        # Return a query-linked excerpt, not the complete page/knowledge collection.
        body = text(item.get('text')) or ''
        body = '\n'.join(line for line in body.splitlines() if not re.match(r'^\s*(?:knowledge_scope|source_name|source_url|checked_at|effective_date|valid_until|scope_notes)\s*[:：]', line))
        terms = re.findall(r'[一-龯ぁ-んァ-ヶ]{2,}|[A-Za-z0-9]+', query)
        position = next((body.find(t) for t in terms if t in body), 0)
        start = max(0, position - 100)
        excerpt = ('…' if start else '') + body[start:start + 600] + ('…' if start + 600 < len(body) else '')
        if excerpt: result.append(CustomerHit(text=excerpt, scope=scope, references=[source(ref, scope)]))
    return result[:8]


def displays(events, session, snapshot):
    result = []
    for event in events:
        raw = obj(event.get('result')); name = event.get('name'); eid = event.get('event_id')
        if event.get('kind') != 'tool' or not isinstance(eid, int) or raw.get('error'): continue
        if name == 'list_properties':
            result.append(CandidatesDisplay(event_id=eid, properties=candidates(snapshot)))
        elif name == 'get_property_overview':
            p = property_view(session, snapshot)
            if p: result.append(PropertyDisplay(event_id=eid, property=p))
        elif name in {'search_property_knowledge', 'search_consultation_knowledge'}:
            items = hits(raw.get('items'), session, snapshot, text(obj(event.get('arguments')).get('query')) or '')
            if items: result.append(SourcesDisplay(event_id=eid, items=items))
        elif name == 'get_mortgage_rates':
            options = products(snapshot)
            if options: result.append(ProductsDisplay(event_id=eid, products=options))
        elif name == 'calculate_mortgage':
            value = mortgage_view(raw, snapshot)
            # Property-based results cease to be current when selection/validity is lost.
            if value and (value.price_basis or property_view(session, snapshot)):
                result.append(MortgageDisplay(event_id=eid, result=value))
    return result


def session_view(store, record, *, created=False):
    try:
        snapshot = snapshot_for(store, record); events = store.events(record['id'])
    except AppError as exc:
        if exc.code != 'SESSION_RESTART_REQUIRED' or record['status'] != 'ended': raise
        # An unsafe legacy session can still be ended without returning history.
        from app.services.context import EMPTY_SNAPSHOT
        snapshot = dict(EMPTY_SNAPSHOT); events = []
    last_user = max((e['event_id'] for e in events if e['kind'] == 'message' and e.get('role') == 'user'), default=0)
    messages = [CustomerMessage(event_id=e['event_id'], role=e['role'], text=text(e.get('text')) or '',
                               created_at=text(e.get('created_at')), channel=e.get('channel') if e.get('channel') in {'text', 'voice', 'policy'} else None,
                               references=sources(e.get('references'), snapshot))
                for e in events if e['kind'] == 'message' and e.get('role') in {'user', 'assistant'}]
    rt = obj(record.get('realtime'))
    rt_status = rt.get('status') if rt.get('status') in {'not_started', 'connecting', 'connected', 'closing', 'closed', 'error', 'disconnected'} else 'error'
    payload = dict(id=record['id'], version=record['version'], mode=record['mode'],
                   property_id=selected(record, snapshot), status=record['status'], created_at=record['created_at'],
                   ended_at=text(record.get('ended_at')), property=property_view(record, snapshot), products=products(snapshot),
                   messages=messages, display_events=displays([e for e in events if e['event_id'] > last_user], record, snapshot),
                   staff_calls=[staff_view(c) for c in store.list('staff_calls') if c.get('session_id') == record['id']],
                   realtime=CustomerRealtime(status=rt_status, error=CustomerVoiceError() if rt_status == 'error' else None))
    return CustomerSessionCreated(token=record['token'], **payload) if created else CustomerSession(**payload)


def answer_view(store, record, raw):
    record = store.get('sessions', record['id']); snapshot = snapshot_for(store, record)
    events = store.events(record['id'])
    last_user = max((e['event_id'] for e in events if e['kind'] == 'message' and e.get('role') == 'user'), default=0)
    call = obj(raw.get('staff_call'))
    own_call = call and call.get('session_id') == record['id']
    return CustomerAnswer(answer=text(raw.get('answer')) or '', version=record['version'],
                          references=sources(raw.get('references'), snapshot),
                          display_events=displays([e for e in events if e['event_id'] > last_user], record, snapshot),
                          staff_call=staff_view(call) if own_call else None)


def realtime_tool_output(name, raw, session, snapshot):
    """Business JSON sent on the provider sideband may also reach its data channel.

    Narrow it too. Upstream arguments/session metadata/audio remain separate,
    unverified channels; ignoring them in JS is not a confidentiality boundary.
    """
    if obj(raw).get('error'):
        code = obj(raw['error']).get('code')
        allowed_codes = {'RATE_NOT_FOUND', 'RATE_CONFIRMATION_REQUIRED', 'SESSION_ENDED', 'RATE_NOT_CURRENT',
                         'PROPERTY_CONTEXT_REQUIRED', 'LOAN_AMOUNT_CONFIRMATION_REQUIRED', 'PROPERTY_PRICE_REQUIRED',
                         'PROPERTY_PRICE_CONFIRMATION_REQUIRED', 'RATE_YEARS_OUTSIDE', 'RATE_AMOUNT_OUTSIDE', 'TOOL_LIMIT'}
        return {'error': {'code': code if code in allowed_codes else 'TOOL_UNAVAILABLE',
                          'message': 'この処理を完了できませんでした。必要な条件を確認するか、スタッフにご相談ください。'}}
    if name == 'call_staff': return staff_view(raw).model_dump()
    if name == 'calculate_mortgage':
        value = mortgage_view(raw, snapshot)
        return value.model_dump() if value else {'error': {'message': '現在有効な試算条件を確認してください。'}}
    if name == 'get_mortgage_rates': return {'rates': [p.model_dump() for p in products(snapshot)]}
    if name == 'list_properties': return {'properties': [p.model_dump() for p in candidates(snapshot)]}
    if name == 'get_property_overview':
        p = property_view(session, snapshot)
        return {'property': p.model_dump(), 'version': snapshot['version']} if p else {'error': {'message': '対象物件を確認してください。'}}
    if name in {'search_property_knowledge', 'search_consultation_knowledge'}:
        return {'items': [i.model_dump() for i in hits(obj(raw).get('items'), session, snapshot)]}
    return {'error': {'message': 'この処理は利用できません。'}}
