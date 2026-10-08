"""Synthetic customer-message authorization tests; no AI/API call involved."""
import pytest

from app.models.domain import AppError
from app.services.loan_selection import require_selected_rate


@pytest.fixture
def snapshot():
    return {'rates': [
        {'id': 'flat35', 'bank': '住宅金融支援機構・取扱金融機関', 'product': 'フラット35 新機構団信付き', 'rate_type': '全期間固定金利'},
        {'id': 'mufg', 'bank': '三菱UFJ銀行', 'product': '住宅ローン 新規借入 優遇金利', 'rate_type': '変動金利'},
    ]}


def message(text, role='user', channel='text', kind='message'):
    return {'kind': kind, 'role': role, 'channel': channel, 'text': text}


def refused(snapshot, events, rate_id='flat35'):
    with pytest.raises(AppError) as error:
        require_selected_rate(snapshot, events, rate_id)
    assert error.value.code == 'RATE_CONFIRMATION_REQUIRED'
    assert 'フラット35' in error.value.message


@pytest.mark.parametrize('events', [
    [], [message('頭金500万円、35年です')], [message('はい')],
    [message('フラット35で計算します', role='assistant'), message('はい')],
    [message('フラット35', kind='tool')], [message('フラット35', channel='policy')],
    [message('フラット35とは何ですか')], [message('フラット35について教えてください')],
    [message('フラット35を選ぶとどうなりますか？')],
    [message('フラット35を選んだことにしてください')],
    [message('フラット35か')], [message('UFJも')], [message('フラット35と')],
    [message('フラット36でお願いします')],
])
def test_non_selection_cannot_authorize(snapshot, events):
    refused(snapshot, events)


@pytest.mark.parametrize('text,rate_id', [
    ('フラット35', 'flat35'), ('ＦＬＡＴ３５でお願いします。', 'flat35'),
    ('頭金500万円、35年、フラット35でお願いします。', 'flat35'),
    ('フラット35（新機構団信付きの21～35年）で、登録されている参考金利を使って概算をお願いします。', 'flat35'),
    ('商品はフラット35です。', 'flat35'), ('固定で計算してください', 'flat35'),
    ('全期間固定金利を選びます', 'flat35'),
    ('UFJ', 'mufg'), ('三菱UFJ銀行の変動金利でお願いします', 'mufg'),
    ('UFJ銀行でお願いします', 'mufg'), ('「フラット35」でお願いします', 'flat35'),
    ('変動金利を希望します', 'mufg'), ('変動で試算してください', 'mufg'),
])
def test_explicit_published_choice_authorizes(snapshot, text, rate_id):
    require_selected_rate(snapshot, [message(text)], rate_id)
    require_selected_rate(snapshot, [message(text, channel='voice')], rate_id)


def test_latest_selection_replaces_previous_and_unrelated_question_does_not(snapshot):
    events = [message('フラット35でお願いします'), message('変動金利に変更してください'), message('駅から何分ですか')]
    require_selected_rate(snapshot, events, 'mufg')
    refused(snapshot, events, 'flat35')


@pytest.mark.parametrize('last', [
    'フラット35は選びません', 'フラット35を使いません',
    'フラット35はやめます', 'フラット35（希望しません）でお願いします',
    'フラット35ではなくUFJでお願いします', 'まだ商品は決めていません',
    'お任せでお願いします', 'フラット35とUFJでお願いします',
])
def test_refusal_or_ambiguity_revokes_previous_choice(snapshot, last):
    refused(snapshot, [message('フラット35'), message(last)])


def test_neutral_reply_does_not_choose_model_proposed_product(snapshot):
    events = [message('フラット35'), message('UFJに変えて計算しますか', role='assistant'), message('はい')]
    refused(snapshot, events, 'mufg')
    require_selected_rate(snapshot, events, 'flat35')


def test_shared_rate_type_or_bank_is_ambiguous(snapshot):
    snapshot['rates'].append({'id': 'other-fixed', 'bank': '別銀行', 'product': '固定期間20年', 'rate_type': '固定金利'})
    refused(snapshot, [message('固定でお願いします')])
    require_selected_rate(snapshot, [message('フラット35でお願いします')], 'flat35')


def test_aliases_are_bound_to_published_labels(snapshot):
    snapshot['rates'] = [snapshot['rates'][0]]
    refused(snapshot, [message('UFJでお願いします')])


def test_unknown_rate_is_left_to_calculator(snapshot):
    assert require_selected_rate(snapshot, [], 'not-published') is None


def test_missing_published_product_label_cannot_establish_selection(snapshot):
    snapshot['rates'] = [{'id': 'flat35'}]
    with pytest.raises(AppError) as error:
        require_selected_rate(snapshot, [message('フラット35でお願いします')], 'flat35')
    assert error.value.code == 'RATE_CONFIRMATION_REQUIRED'

def test_property_undecided_does_not_revoke_explicit_loan_product(snapshot):
    require_selected_rate(snapshot,[message('物件はまだ決めていません。借入額は三千万円です。35年です。三菱UFJ銀行の変動金利でお願いします。')],'mufg')
    require_selected_rate(snapshot,[message('三菱UFJ銀行でお願いします'),message('物件はまだ決めていません')],'mufg')
    refused(snapshot,[message('フラット35'),message('ローン商品はまだ決めていません')])
