"""Explicit property context shared by text and recognized voice input."""
import re
import unicodedata
from app.models.domain import AppError, now
from datetime import date

EMPTY_SNAPSHOT = {'property': {}, 'knowledge': [], 'faq': [], 'rates': [], 'references': [], 'document_ids': [], 'version': None}

def raw_snapshot_for(store, session):
    return store.version(session['version']) if session.get('version') else dict(EMPTY_SNAPSHOT)

def snapshot_for(store, session):
    from app.services.knowledge_access import available_snapshot, require_boundary
    snapshot = raw_snapshot_for(store, session)
    require_boundary(store, session, snapshot)
    out = available_snapshot(store, snapshot)
    out['rates'] = [r for r in out['rates'] if r.get('scope') != 'property' or session.get('property_id') == property_id(out)]
    return out

def property_id(snapshot):
    return snapshot.get('property', {}).get('lot')

def selected(session, snapshot):
    return session.get('property_id')

def validate_property(snapshot,id,today=None):
    if not snapshot.get('version'): raise AppError('NO_PUBLISHED_DATA','公開済み物件資料がありません。',409)
    if snapshot.get('_property_error'):
        raise AppError(snapshot['_property_error'], '対象物件資料の適用期間を確認してください。', 409)
    if not id or id != property_id(snapshot): raise AppError('PROPERTY_NOT_FOUND','この接客版に対象物件がありません。',404)
    p=snapshot['property'];today=today or date.fromisoformat(now()[:10])
    if not p.get('valid_until') or date.fromisoformat(str(p['valid_until'])[:10])<today: raise AppError('PROPERTY_EXPIRED','対象物件資料の有効期限を確認してください。',409)
    if p.get('effective_date') and date.fromisoformat(str(p['effective_date'])[:10])>today: raise AppError('PROPERTY_NOT_YET_EFFECTIVE','対象物件資料はまだ有効ではありません。',409)

def bind(store, session, id):
    snapshot = snapshot_for(store, session)
    validate_property(snapshot,id)
    record=store.get('sessions',session['id'])
    if record['status'] != 'active': raise AppError('SESSION_ENDED', '接客は終了しています。', 409)
    record['property_id']=id;store.put('sessions',record)
    return record


def customer_snapshot(session, snapshot):
    """Avoid fetching specific-property facts into an unselected Customer UI."""
    if selected(session, snapshot): return snapshot
    result=dict(snapshot, property={})
    for section in ('knowledge','faq'):
        result[section]=[i for i in snapshot.get(section,[]) if i.get('scope','property') in {'general','company'}]
    rate_documents={r.get('reference',{}).get('document_id') for r in snapshot.get('rates',[])}
    validity=snapshot.get('document_validity',{})
    result['references']=[ref for ref in snapshot.get('references',[]) if ref.get('document_id') in rate_documents or validity.get(ref.get('document_id'),{}).get('scope') in {'general','company'}]
    return result


def declared_number(text):
    """Parse literal customer currency notation, including Japanese ASR numerals."""
    text=text.replace(',','')
    if re.fullmatch(r'[0-9.]+',text): return float(text)
    digits={'零':0,'〇':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
    small={'十':10,'百':100,'千':1000};large={'万':10000,'億':100000000}
    total=section=0;number=''
    for ch in text:
        if ch in digits: number+=str(digits[ch])
        elif ch.isdigit() or ch=='.': number+=ch
        elif ch in small:
            section+=(float(number) if number else 1)*small[ch];number=''
        elif ch in large:
            total+=(section+(float(number) if number else 0) or 1)*large[ch];section=0;number=''
        else: raise ValueError('Invalid declared amount')
    return total+section+(float(number) if number else 0)


def observe_customer(store, session, text):
    snapshot=snapshot_for(store,session);id=property_id(snapshot)
    text=unicodedata.normalize('NFKC',text)
    record=store.get('sessions',session['id'])
    currency=r'([0-9,.零〇一二三四五六七八九十百千万億]+)\s*(万円|万|円)'
    for key,prefix in [('declared_loan_amount',r'(?:借(?:入|り入れ)(?:額|金額)?|借りたい(?:金額)?|借りる(?:金額)?)'),('declared_property_price',r'(?:取得価格|物件価格|購入価格|住宅価格)')]:
        m=re.search(prefix+r'\s*(?:は|を|が)?\s*'+currency,text)
        if not m and key=='declared_loan_amount': m=re.search(currency+r'\s*(?:を)?\s*借り(?:たい|ます|る)',text)
        if m:
            value=declared_number(m[1])*(10000 if m[2] in {'万円','万'} else 1)
            if 0<value<=1000000000: record[key]=value
    if re.search(r'物件.*(?:まだ決めていません|未定|未選択)|一般相談に戻',text): record['property_id']=None
    requested=re.search(r'No\.?\s*(\d+)|(\d+)号(?:地)?',text,re.I)
    target=re.search(r'\d+',id or '')
    if requested:
        number=requested[1] or requested[2]
        rejected=re.match(r'(?:ではなく|ではない|以外|じゃなく|は選びません)',text[requested.end():])
        if rejected or not target or number!=target[0]:
            record['property_id']=None
        else:
            store.put('sessions',record)
            return bind(store,record,id)
    store.put('sessions',record)
    return record
