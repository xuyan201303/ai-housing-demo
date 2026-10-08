"""Explicit, source-checked provider payload shared by Responses and Realtime."""
import re
from app.schemas.ai_evidence import AiEvidence, EvidenceItem, EvidenceError, EvidenceProduct, CustomerDeclaration
from app.services.context import snapshot_for, selected
from app.services.customer_view import property_view, candidates, products, mortgage_view, staff_view, source, number, obj

MAX_EVIDENCE_CHARS = 18000
ERROR_CODES = frozenset({'RATE_NOT_FOUND', 'RATE_CONFIRMATION_REQUIRED', 'SESSION_ENDED',
    'RATE_NOT_CURRENT', 'PROPERTY_CONTEXT_REQUIRED', 'LOAN_AMOUNT_CONFIRMATION_REQUIRED',
    'PROPERTY_PRICE_REQUIRED', 'PROPERTY_PRICE_CONFIRMATION_REQUIRED', 'RATE_YEARS_OUTSIDE',
    'RATE_AMOUNT_OUTSIDE', 'TOOL_LIMIT', 'NO_CURRENT_RATES', 'PROPERTY_EXPIRED',
    'PROPERTY_NOT_YET_EFFECTIVE', 'LOAN_AMOUNT_REQUIRED', 'SESSION_RESTART_REQUIRED'})


def error_evidence(code):
    return AiEvidence(error=EvidenceError(code=code if code in ERROR_CODES else 'TOOL_UNAVAILABLE')).model_dump(exclude_none=True)


def matched_items(raw, session, snapshot):
    allowed = snapshot.get('knowledge', []) + [dict(text=f"{i['question']}\n{i['answer']}", scope=i.get('scope', 'property'), reference=i['reference']) for i in snapshot.get('faq', [])]
    values = []
    for item in raw if isinstance(raw, list) else []:
        item = obj(item)
        content = item.get('text') or (f"{item['question']}\n{item['answer']}" if 'question' in item and 'answer' in item else None)
        scope = item.get('scope', 'property'); doc = obj(item.get('reference')).get('document_id')
        if scope == 'property' and property_view(session, snapshot) is None: continue
        match = next((i for i in allowed if i.get('text') == content and i.get('scope', 'property') == scope and obj(i.get('reference')).get('document_id') == doc), None)
        if match is not None:
            values.append(match)
    return values


def evidence_items(raw, session, snapshot):
    return [EvidenceItem(text=i['text'], scope=i.get('scope', 'property'),
                         references=[source(i['reference'], i.get('scope', 'property'))])
            for i in matched_items(raw, session, snapshot)]


def prioritize_exact_faq(items, snapshot, query):
    """Prefer an approved FAQ only when its complete question matches.

    Broad/partial consultation retains the existing relevance filtering. This
    never adds an FAQ that was absent from the permitted Tool result.
    """
    if not isinstance(query, str) or not query.strip(): return items, False
    def key(value):
        return re.sub(r'\s+', '', value).rstrip('？?。.!！')
    exact = {(f"{f['question']}\n{f['answer']}", f.get('scope', 'property'))
             for f in snapshot.get('faq', [])
             if key(f['question']) == key(query)}
    matches = [i for i in items if (i.text, i.scope) in exact]
    return (matches, True) if matches else (items, False)


def tool_references(store, session, name, raw, evidence):
    """Bind answer citations to facts actually admitted to provider evidence.

    Keep internal source identities for the existing Customer projection. Do
    not collect the entire context's source list or accept model-made links.
    """
    if obj(evidence).get('error'): return []
    snapshot = snapshot_for(store, session)
    refs = []
    admitted = {(i['text'], i['scope']) for i in evidence.get('items', [])}
    for item in matched_items(obj(raw).get('items'), session, snapshot):
        if (item['text'], item.get('scope', 'property')) in admitted:
            refs.append(item['reference'])
    if evidence.get('property'):
        validity = snapshot.get('document_validity', {})
        refs.extend(r for r in snapshot.get('references', [])
                    if obj(validity.get(obj(r).get('document_id'))).get('scope', 'property') == 'property')
    if name == 'get_mortgage_rates':
        ids = {p['id'] for p in evidence.get('rates', [])}
        refs.extend(r['reference'] for r in snapshot.get('rates', []) if r.get('id') in ids)
    elif name == 'calculate_mortgage' and evidence.get('mortgage'):
        refs.extend(r for r in obj(raw).get('references', [])
                    if obj(r).get('document_id') in snapshot.get('document_ids', []))
    return refs


def tool_evidence(store, session, name, raw, *, query=None):
    snapshot = snapshot_for(store, session)
    if obj(raw).get('error'): return error_evidence(obj(raw['error']).get('code'))
    out = AiEvidence(version=snapshot.get('version'))
    if name == 'get_consultation_context':
        record = store.get('sessions', session['id'])
        out.property_selected = bool(selected(record, snapshot))
        out.customer_declared = CustomerDeclaration(loan_amount=number(record.get('declared_loan_amount')), property_price=number(record.get('declared_property_price')))
        out.items = evidence_items(obj(raw).get('items'), record, snapshot)
        out.company_material_available = any(i.get('scope') == 'company' for i in snapshot['knowledge'] + snapshot['faq'])
        out.items, exact_faq = prioritize_exact_faq(out.items, snapshot, query)
        if query is not None:
            terms = re.findall(r'[A-Za-z0-9]+|[一-龯ぁ-んァ-ヶ]{2,}', query[:500])
            if not exact_faq:
                out.items = [i for i in out.items if query and (any(t in i.text for t in terms) or any(query[n:n+2] in i.text for n in range(len(query)-1)))]
        if query != '' and not exact_faq: out.property = property_view(record, snapshot)
    elif name == 'list_properties': out.properties = candidates(snapshot)
    elif name == 'get_property_overview': out.property = property_view(session, snapshot)
    elif name in {'search_property_knowledge', 'search_consultation_knowledge'}:
        out.items = evidence_items(obj(raw).get('items'), session, snapshot)
        if name == 'search_consultation_knowledge':
            out.items, _ = prioritize_exact_faq(out.items, snapshot, query)
    elif name == 'get_mortgage_rates':
        for p in products(snapshot):
            if p.rate_over_90_percent is not None:
                condition = f'融資率9割以下の参考金利: {p.rate}%。9割超の参考金利: {p.rate_over_90_percent}%。この区分はこの商品だけに適用。'
            elif p.max_loan_to_value is not None: condition = f'公開資料の融資率上限（比率）: {p.max_loan_to_value}。'
            else: condition = '融資率による金利区分・上限はこの商品の資料には未登録です。別商品の条件を転用しないでください。'
            out.rates.append(EvidenceProduct(**p.model_dump(), loan_to_value_conditions=condition))
    elif name == 'calculate_mortgage': out.mortgage = mortgage_view(raw, snapshot)
    elif name == 'call_staff':
        # Re-read this Session's record instead of trusting a raw service object.
        call = store.get('staff_calls', obj(raw).get('id', ''))
        if call.get('session_id') == session['id']: out.staff_call = staff_view(call)
    else: return error_evidence('TOOL_UNAVAILABLE')
    if out.property:
        out.property_scope_conditions = snapshot.get('_property_scope_conditions', [])
    if len(out.model_dump_json()) > MAX_EVIDENCE_CHARS:
        # Never clip evidence, including negations or the end of rate conditions.
        return AiEvidence(version=snapshot.get('version'), error=EvidenceError(code='EVIDENCE_BUDGET_EXCEEDED', message='資料が多いため、この結果を根拠に回答できません。質問を絞って資料を検索するか、スタッフに確認してください。')).model_dump(exclude_none=True)
    return out.model_dump(exclude_none=True)
