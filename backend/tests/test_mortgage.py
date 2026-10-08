from knowledge_fixtures import approve_fixture, stamp_session
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.models import domain
from app.models.domain import AppError
from app.repositories.store import Store
from app.services.mortgage import calculate_from_snapshot, calculate_mortgage
from app.services.staff import StaffService
from app.services.tools import ToolService


@pytest.fixture(autouse=True)
def fixed_tokyo_clock(monkeypatch):
    monkeypatch.setattr(domain, 'now', lambda: '2026-10-07T12:00:00+09:00')


@pytest.fixture
def snapshot():
    return {
        'version': 1, 'published_at': '2026-10-07T10:00:00+09:00',
        'property': {'price': 76900000, 'property_name': '公開物件 No.15'},
        'rates': [{
            'id': 'flat35', 'bank': '住宅金融支援機構・取扱金融機関',
            'product': 'フラット35 新機構団信付き', 'rate_type': '全期間固定',
            'rate': 3.83, 'rate_over_90_percent': 3.94,
            'effective_date': '2026-10-01', 'valid_until': '2026-10-31',
            'years_min': 21, 'years_max': 35,
            'loan_amount_min': 1000000, 'loan_amount_max': 120000000,
            'max_loan_to_value': 1, 'notes': '資金受取時金利。審査あり。',
            'reference': {'document_id': 'rates-doc', 'filename': '住宅ローン_demo.xlsx'},
        }],
    }


def test_known_equal_payment_value():
    # Independently tabulated 30m JPY, 1% annual, 35 years: 84,685.71 JPY.
    result = calculate_mortgage(35000000, 5000000, 30000000, 1, 35)
    assert result['monthly_payment'] == 84686
    assert result['loan_amount'] == 30000000
    assert result['calculation_date'] == '2026-10-07'
    assert '概算' in result['notes']


def test_zero_interest_and_zero_loan():
    assert calculate_mortgage(12000000, 0, 12000000, 0, 10)['monthly_payment'] == 100000
    assert calculate_mortgage(1000000, 1000000, 0, 2, 10)['monthly_payment'] == 0


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), float('-inf'), 'NaN', 'Infinity', True])
def test_rejects_nonfinite_and_boolean_money(bad):
    with pytest.raises(AppError):
        calculate_mortgage(30000000, bad, 30000000, 1, 35)
    with pytest.raises(AppError):
        calculate_mortgage(30000000, 0, 30000000, bad, 35)


@pytest.mark.parametrize('years', [0, 51, 35.5, True])
def test_rejects_invalid_term(years):
    with pytest.raises(AppError):
        calculate_mortgage(30000000, 0, 30000000, 1, years)


def test_rejects_mismatched_amounts():
    with pytest.raises(AppError, match='関係'):
        calculate_mortgage(30000000, 5000000, 30000000, 1, 35)


def test_published_rate_selects_ltv_tier_at_exact_boundary(snapshot):
    low = calculate_from_snapshot(snapshot, 7690000, 35, 'flat35')
    assert low['annual_interest_rate'] == 3.83
    assert low['loan_to_value_percent'] == 90
    high = calculate_from_snapshot(snapshot, 7689999, 35, 'flat35')
    assert high['annual_interest_rate'] == 3.94
    assert high['references'][0]['document_id'] == 'rates-doc'
    assert high['property_price'] == 76900000
    assert snapshot['rates'][0]['rate'] == 3.83  # Session snapshot stays immutable.


def test_reference_tool_keeps_flat_ltv_bands_separate_from_unregistered_bank_condition(tmp_path, snapshot):
    bank_rate = dict(snapshot['rates'][0], id='mufg', bank='三菱UFJ銀行', product='住宅ローン', rate=1.195)
    del bank_rate['rate_over_90_percent']
    del bank_rate['max_loan_to_value']
    snapshot['rates'].append(bank_rate)
    store = Store(tmp_path / 'rate-context.db'); store.init()
    snapshot = approve_fixture(store, snapshot)
    with store.connect() as db:
        db.execute('INSERT INTO versions(version,payload) VALUES (?,?)', (1, json.dumps(snapshot)))
    session = {'id': 'TEST-rate-context', 'status': 'active', 'version': 1}
    session.setdefault('property_id', 'No.15')
    stamp_session(store, session)
    result = ToolService(store).execute(session, 'get_mortgage_rates', {})
    flat, bank = result['rates']
    assert '9割以下' in flat['loan_to_value_conditions'] and '3.94' in flat['loan_to_value_conditions']
    assert '未登録' in bank['loan_to_value_conditions']
    assert '転用しない' in bank['loan_to_value_conditions']
    assert 'loan_to_value_conditions' not in store.version(1)['rates'][0]


def test_refuses_unconfirmed_high_ltv_tier(snapshot):
    del snapshot['rates'][0]['rate_over_90_percent']
    with pytest.raises(AppError) as exc:
        calculate_from_snapshot(snapshot, 5000000, 35, 'flat35')
    assert exc.value.code == 'RATE_LTV_UNCONFIRMED'


@pytest.mark.parametrize('key,value', [('effective_date', '2026-10-08'), ('valid_until', '2026-10-06'), ('effective_date', ''), ('valid_until', None)])
def test_rejects_future_expired_or_missing_dates(snapshot, key, value):
    snapshot['rates'][0][key] = value
    with pytest.raises(AppError) as exc:
        calculate_from_snapshot(snapshot, 10000000, 35, 'flat35')
    assert exc.value.code in {'RATE_NOT_CURRENT', 'INVALID_RATE_DATE'}


def test_validity_boundaries_are_inclusive(snapshot):
    snapshot['rates'][0].update(effective_date='2026-10-07', valid_until='2026-10-07')
    assert calculate_from_snapshot(snapshot, 10000000, 35, 'flat35')['monthly_payment'] > 0


def test_product_bounds_are_enforced(snapshot):
    with pytest.raises(AppError) as exc:
        calculate_from_snapshot(snapshot, 10000000, 20, 'flat35')
    assert exc.value.code == 'RATE_YEARS_OUTSIDE'
    with pytest.raises(AppError) as exc:
        calculate_from_snapshot(snapshot, 76900000, 35, 'flat35')
    assert exc.value.code == 'RATE_AMOUNT_OUTSIDE'
    del snapshot['rates'][0]['loan_amount_min']
    with pytest.raises(AppError) as exc:
        calculate_from_snapshot(snapshot, 10000000, 35, 'flat35')
    assert exc.value.code == 'RATE_CONDITIONS_REQUIRED'


def test_unpublished_and_other_version_rates_are_unavailable(snapshot):
    snapshot.pop('published_at')
    with pytest.raises(AppError) as exc:
        calculate_from_snapshot(snapshot, 10000000, 35, 'flat35')
    assert exc.value.code == 'UNPUBLISHED_RATES'
    snapshot['published_at'] = '2026-10-07T10:00:00+09:00'
    with pytest.raises(AppError) as exc:
        calculate_from_snapshot(snapshot, 10000000, 35, 'other-version-rate')
    assert exc.value.code == 'RATE_NOT_FOUND'


def test_staff_lifecycle_persists_and_active_calls_are_idempotent(tmp_path, snapshot):
    store = Store(tmp_path / 'staff.db')
    store.init()
    snapshot = approve_fixture(store, snapshot)
    with store.connect() as db:
        db.execute('INSERT INTO versions(version,payload) VALUES (?,?)', (1, json.dumps(snapshot)))
    session = {'id': 'session-1', 'status': 'active', 'version': 1}
    session.setdefault('property_id', 'No.15')
    stamp_session(store, session)
    service = StaffService(store)
    with ThreadPoolExecutor(max_workers=4) as pool:
        calls = list(pool.map(lambda _: service.call(session, '担当スタッフへ相談', '審査は通りますか？'), range(4)))
    assert len({call['id'] for call in calls}) == 1
    call = calls[0]
    assert len(store.list('staff_calls')) == 1
    assert call['property_name'] == snapshot['property']['property_name']
    with pytest.raises(AppError) as exc:
        service.transition(call['id'], 'completed')
    assert exc.value.code == 'INVALID_STAFF_TRANSITION'
    accepted = service.transition(call['id'], 'accepted')
    assert service.call(session, '追加相談')['id'] == call['id']
    assert accepted['accepted_at']
    completed = service.transition(call['id'], 'completed')
    assert completed['completed_at']
    assert store.get('staff_calls', call['id'])['status'] == 'completed'
    assert [event['action'] for event in store.events(session['id'])] == ['created', 'accepted', 'completed']
    # Repeated browser submission does not create an extra transition event.
    service.transition(call['id'], 'completed')
    assert len(store.events(session['id'])) == 3
    assert service.call(session, '新しい相談')['id'] != call['id']
