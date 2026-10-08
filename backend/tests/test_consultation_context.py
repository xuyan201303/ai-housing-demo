"""TEST-only scope/property/loan guards; no external AI or normal DB writes."""
import copy
import json
from types import SimpleNamespace
from pathlib import Path
import pytest
from app.models.domain import AppError
from app.repositories.store import Store
from app.services.documents import DocumentService
from app.services.sessions import SessionService
from app.services.tools import ToolService
from app.services.context import observe_customer
from app.services.guardrails import consultation_policy
ROOT=Path(__file__).resolve().parents[2]
@pytest.fixture
def system(tmp_path):
    store=Store(tmp_path/'test.db');store.init()
    docs=DocumentService(store,SimpleNamespace(upload_dir=tmp_path/'uploads',max_upload_bytes=10*1024*1024))
    return store,docs,SessionService(store),ToolService(store)
def prepare(docs, filename):
    p=ROOT/'demo_documents'/filename
    return docs.parse(docs.upload(p.name,p.read_bytes())['id'])
def confirm(docs,record):
    review=copy.deepcopy(record['normalized'])
    if review.get('rates') and not review.get('property'):
        review['document']={'scope':'general','source_name':'TEST approved rate source','source_url':review['rates'][0]['source_url'],'checked_at':'2026-10-07','effective_date':'2026-10-01','valid_until':'2026-10-15'}
    return docs.confirm(record['id'],review,'TEST scope review; not human normal acceptance', usage='customer')
def test_start_without_published_materials_and_general_staff(system):
    store,docs,sessions,tools=system
    s=sessions.start('text');assert s['version'] is None and s['property_id'] is None
    context=tools.execute(s,'get_consultation_context',{})
    assert context['items']==[] and 'property' not in context
    assert 'どの物件' in consultation_policy(s,context,'駅から何分ですか？')
    assert 'まだ' in consultation_policy(s,context,'営業時間は何時ですか？')
    call=tools.execute(s,'call_staff',{'reason':'一般相談'})
    assert call['version'] is None and call['property_name']=='住宅購入の一般相談'
    tools.staff.transition(call['id'],'accepted');tools.staff.transition(call['id'],'completed')
    assert sessions.view(s)['staff_calls'][0]['status']=='completed'
def test_general_source_sdk_parse_confirmation_publication_and_pinning(system):
    store,docs,sessions,tools=system
    old=sessions.start('text')
    record=prepare(docs,'住宅購入基礎FAQ_demo.pdf')
    assert record['sdk_version']=='1.8.0' and record['raw']['pages']
    assert record['normalized']['property']=={} and record['normalized']['document']['scope']=='general'
    with pytest.raises(AppError) as exc: docs.publish([record['id']])
    assert exc.value.code=='UNCONFIRMED_DOCUMENT'
    reviewed=confirm(docs,record)
    assert all(i['reference']['source_url'].startswith('https://www.mlit.go.jp/') for i in reviewed['reviewed']['knowledge'])
    published=docs.publish([record['id']]);assert published['property']=={}
    current=sessions.start('voice');context=tools.execute(current,'get_consultation_context',{})
    assert context['items'] and all(i['scope']=='general' for i in context['items']) and 'property' not in context
    assert tools.execute(old,'get_consultation_context',{})['items']==[]
    company=tools.execute(current,'search_consultation_knowledge',{'query':'重要事項','scope':'company'})
    assert company['items']==[]
    hits=tools.execute(current,'search_consultation_knowledge',{'query':'重要事項','scope':'general'})
    assert hits['items'] and all(i['reference']['document_id']==record['id'] for i in hits['items'])
def test_no_implicit_property_read_or_price_and_explicit_binding(system):
    store,docs,sessions,tools=system
    p=confirm(docs,prepare(docs,'物件概要_demo.pdf'));rates=confirm(docs,prepare(docs,'住宅ローン_demo.xlsx'))
    snapshot=docs.publish([p['id'],rates['id']]);s=sessions.start('text')
    assert s['property_id'] is None and 'property' not in tools.execute(s,'get_consultation_context',{})
    for name,args in [('get_property_overview',{}),('search_property_knowledge',{'query':'駅'})]:
        with pytest.raises(AppError) as exc: tools.execute(s,name,args)
        assert exc.value.code=='PROPERTY_CONTEXT_REQUIRED'
    flat=next(r for r in snapshot['rates'] if 'フラット' in r['product'])
    mufg=next(r for r in snapshot['rates'] if '三菱' in r['bank'])
    args={'loan_amount':30000000,'years':35,'rate_id':flat['id']}
    with pytest.raises(AppError) as exc: tools.execute(s,'calculate_mortgage',args)
    assert exc.value.code=='PROPERTY_PRICE_REQUIRED'
    explicit=tools.execute(s,'calculate_mortgage',dict(args,property_price=40000000))
    assert explicit['property_price']==40000000 and explicit['loan_amount']==30000000 and explicit['annual_interest_rate']==3.83
    result=tools.execute(s,'calculate_mortgage',dict(args,rate_id=mufg['id']))
    assert result['property_price'] is None and result['down_payment'] is None and result['loan_amount']==30000000
    with pytest.raises(AppError) as exc: tools.execute(s,'calculate_mortgage',dict(args,loan_amount=None))
    assert exc.value.code=='LOAN_AMOUNT_REQUIRED'
    s=observe_customer(store,s,'借入額は3000万円です。購入価格は4000万円です。')
    assert s['declared_loan_amount']==30000000 and s['declared_property_price']==40000000 and s['property_id'] is None
    s=observe_customer(store,s,'No.15の設備を教えてください。')
    assert s['property_id']=='No.15'
    assert tools.execute(s,'get_property_overview',{})['property']['price']==76900000
@pytest.mark.parametrize('channel',['text','voice'])
def test_ai_declared_amount_and_product_cannot_be_invented(system,channel):
    store,docs,sessions,tools=system
    rates=confirm(docs,prepare(docs,'住宅ローン_demo.xlsx'));snapshot=docs.publish([rates['id']]);s=sessions.start(channel)
    rate=next(r for r in snapshot['rates'] if '三菱' in r['bank'])
    args={'loan_amount':30000000,'years':35,'rate_id':rate['id']}
    store.event(s['id'],'message',{'role':'user','text':'35年です','channel':channel})
    with pytest.raises(AppError) as exc: tools.execute(s,'calculate_mortgage',args,ai_requested=True)
    assert exc.value.code=='RATE_CONFIRMATION_REQUIRED'
    store.event(s['id'],'message',{'role':'user','text':'三菱UFJ銀行でお願いします','channel':channel})
    with pytest.raises(AppError) as exc: tools.execute(s,'calculate_mortgage',args,ai_requested=True)
    assert exc.value.code=='LOAN_AMOUNT_CONFIRMATION_REQUIRED'
    observe_customer(store,s,'借入額は3000万円です')
    result=tools.execute(s,'calculate_mortgage',args,ai_requested=True)
    assert result['property_price'] is None and result['version']==s['version']
def test_common_source_and_property_scope_conflict_rejected(system):
    store,docs,sessions,tools=system;record=prepare(docs,'住宅購入基礎FAQ_demo.pdf')
    review=copy.deepcopy(record['normalized']);review['document'].pop('source_url')
    with pytest.raises(AppError) as exc: docs.confirm(record['id'],review,'TEST', usage='customer')
    assert exc.value.code=='KNOWLEDGE_SOURCE_REQUIRED'
    review=copy.deepcopy(record['normalized']);review['property']={'price':76900000}
    with pytest.raises(AppError) as exc: docs.confirm(record['id'],review,'TEST', usage='customer')
    assert exc.value.code=='SCOPE_PROPERTY_CONFLICT'

def test_common_expiry_does_not_return_stale_facts(system,monkeypatch):
    store,docs,sessions,tools=system
    record=confirm(docs,prepare(docs,'住宅購入基礎FAQ_demo.pdf'));docs.publish([record['id']]);s=sessions.start('text')
    monkeypatch.setattr('app.services.tools.now',lambda:'2026-11-07T12:00:00+09:00')
    assert tools.execute(s,'get_consultation_context',{})['items']==[]
    assert tools.execute(s,'search_consultation_knowledge',{'query':'重要事項','scope':'general'})['items']==[]

def test_general_cannot_expose_expired_selected_property(system,monkeypatch):
    store,docs,sessions,tools=system
    prop=confirm(docs,prepare(docs,'物件概要_demo.pdf'));general=confirm(docs,prepare(docs,'住宅購入基礎FAQ_demo.pdf'))
    docs.publish([prop['id'],general['id']]);s=sessions.start('text','No.15')
    monkeypatch.setattr('app.services.context.now',lambda:'2026-10-16T12:00:00+09:00')
    monkeypatch.setattr('app.services.tools.now',lambda:'2026-10-16T12:00:00+09:00')
    context=tools.execute(s,'get_consultation_context',{})
    assert context['items'] and 'property' not in context and context['property_error']['code']=='PROPERTY_EXPIRED'
    assert all(r['document_id']==general['id'] for r in context['references'])

@pytest.mark.parametrize('text,amount',[
 ('借入額は三千万円です。',30000000),('借入額は3,000万円です。',30000000),
 ('三千万円を借りたいです。',30000000),('借り入れ金額は一億二千万円です。',120000000),
 ('借入額は3千万円です。',30000000),('借入額は３０００万円です。',30000000),
])
def test_customer_literal_currency_handles_real_japanese_asr(system,text,amount):
    store,docs,sessions,tools=system;s=sessions.start('voice')
    assert observe_customer(store,s,text)['declared_loan_amount']==amount

def test_session_payload_masks_unselected_property_and_context_can_be_revoked(system):
    store,docs,sessions,tools=system
    p=confirm(docs,prepare(docs,'物件概要_demo.pdf'));r=confirm(docs,prepare(docs,'住宅ローン_demo.xlsx'));docs.publish([p['id'],r['id']])
    s=sessions.start('text');assert s['snapshot']['property']=={} and s['snapshot']['knowledge']==[] and s['snapshot']['rates']
    s=observe_customer(store,s,'No.15の価格を教えてください')
    assert sessions.view(s)['snapshot']['property']['price']==76900000
    s=observe_customer(store,s,'物件はまだ決めていません。一般相談に戻ります。')
    assert s['property_id'] is None and sessions.view(s)['snapshot']['property']=={}
    s=observe_customer(store,s,'No.14の価格は？')
    assert s['property_id'] is None
    with pytest.raises(AppError) as exc: tools.execute(s,'search_consultation_knowledge',{'query':'価格','scope':'property'})
    assert exc.value.code=='INVALID_KNOWLEDGE_SCOPE'


def test_general_loan_capacity_question_is_not_property_price_question(system):
    store,docs,sessions,tools=system;s=sessions.start('text');context=tools.execute(s,'get_consultation_context',{})
    assert consultation_policy(s,context,'いくら借りられますか？') is None
    assert 'どの物件' in consultation_policy(s,context,'いくらですか？')
