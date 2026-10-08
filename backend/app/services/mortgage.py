"""JPY reference calculation from a session's immutable published snapshot."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from zoneinfo import ZoneInfo

from app.models import domain
from app.models.domain import AppError


DISCLAIMER = '本結果は概算です。実際の適用金利・融資条件等は金融機関により異なります。'
CALCULATION_NOTES = (
    DISCLAIMER + '元利均等・毎月返済・ボーナス返済なし。'
    '金利を返済期間中一定と仮定し、月額を1円単位に四捨五入しています。'
    '手数料・税・保険料は含まず、変動金利の将来変化や融資審査は予測しません。'
)


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise AppError('INVALID_MORTGAGE_NUMBER', f'{label} の数値を確認してください。')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise AppError('INVALID_MORTGAGE_NUMBER', f'{label} の数値を確認してください。')
    if not result.is_finite():
        raise AppError('INVALID_MORTGAGE_NUMBER', f'{label} は有限の数値で入力してください。')
    return result


def _years(value):
    result = _number(value, '返済期間')
    if result != result.to_integral_value() or not 1 <= result <= 50:
        raise AppError('INVALID_MORTGAGE_YEARS', '返済期間は1～50年の整数で入力してください。')
    return int(result)


def _json_number(value):
    return int(value) if value == value.to_integral_value() else float(value)


def _today():
    # Domain clock is the application's single Tokyo clock, also injectable in tests.
    return datetime.fromisoformat(domain.now()).astimezone(ZoneInfo('Asia/Tokyo')).date()


def calculate_mortgage(property_price, down_payment, loan_amount, annual_interest_rate, years):
    """Pure equal-payment formula; never called with unvalidated AI arithmetic.

    Amounts are JPY, interest is annual percent (1.195 means 1.195%). A zero
    loan returns zero; published-product validation can reject it separately.
    """
    price = _number(property_price, '物件価格')
    down = _number(down_payment, '頭金')
    principal = _number(loan_amount, '借入額')
    annual = _number(annual_interest_rate, '年利')
    period = _years(years)
    if not 0 < price <= Decimal('1000000000'):
        raise AppError('INVALID_MORTGAGE_PRICE', '物件価格を確認してください。')
    if not 0 <= down <= price or not 0 <= principal <= price or principal != price - down:
        raise AppError('INVALID_MORTGAGE_AMOUNT', '頭金・借入額と物件価格の関係を確認してください。')
    if not 0 <= annual <= 20:
        raise AppError('INVALID_MORTGAGE_RATE', '年利は0～20%で入力してください。')
    with localcontext() as context:
        context.prec = 60
        months = period * 12
        monthly_rate = annual / Decimal('1200')
        if not monthly_rate:
            payment = principal / months
        else:
            # Equivalent to P*r*(1+r)^n / ((1+r)^n-1), avoiding the
            # cancellation in the positive-power denominator for normal rates.
            denominator = 1 - (1 + monthly_rate) ** -months
            if denominator == 0:
                # Rates below Decimal resolution round to zero yen influence.
                payment = principal / months
            else:
                payment = principal * monthly_rate / denominator
        monthly_payment = int(payment.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return {
        'property_price': _json_number(price), 'down_payment': _json_number(down),
        'loan_amount': _json_number(principal), 'annual_interest_rate': _json_number(annual),
        'years': period, 'monthly_payment': monthly_payment,
        'calculation_date': _today().isoformat(), 'notes': CALCULATION_NOTES,
    }


def _rate_dates(rate):
    try:
        start = date.fromisoformat(rate['effective_date'])
        end = date.fromisoformat(rate['valid_until'])
    except (KeyError, TypeError, ValueError):
        raise AppError('INVALID_RATE_DATE', '参考金利の有効期間が未確認です。スタッフにご確認ください。', 409)
    if start > end:
        raise AppError('INVALID_RATE_DATE', '参考金利の有効期間が不正です。', 409)
    if not start <= _today() <= end:
        raise AppError('RATE_NOT_CURRENT', '参考金利は現在の基準日に適用できません。管理画面で再確認してください。', 409)
    return start, end


def _boundaries(rate):
    values = {}
    for key in ['years_min', 'years_max', 'loan_amount_min', 'loan_amount_max']:
        if key not in rate or rate[key] in ('', None):
            raise AppError('RATE_CONDITIONS_REQUIRED', '参考金利の返済期間・借入額条件を管理画面で確認してください。', 409)
        values[key] = _number(rate[key], key)
    if (
        values['years_min'] != values['years_min'].to_integral_value()
        or values['years_max'] != values['years_max'].to_integral_value()
        or not 1 <= values['years_min'] <= values['years_max'] <= 50
        or not 0 < values['loan_amount_min'] <= values['loan_amount_max']
    ):
        raise AppError('INVALID_RATE_CONDITIONS', '参考金利の適用条件が不正です。', 409)
    return values


def calculate_from_snapshot(snapshot, down_payment, years, rate_id):
    """Use only published price/rate facts; preserve source and LTV conditions."""
    if not snapshot.get('version') or not snapshot.get('published_at'):
        raise AppError('UNPUBLISHED_RATES', '確認・公開済みの金利のみ使用できます。', 409)
    matches = [rate for rate in snapshot.get('rates', []) if rate.get('id') == rate_id]
    if len(matches) != 1:
        raise AppError('RATE_NOT_FOUND', 'この公開版で参考金利を確認できません。', 404)
    rate = matches[0]
    start, end = _rate_dates(rate)
    boundaries = _boundaries(rate)
    price = _number(snapshot.get('property', {}).get('price'), '公開済み物件価格')
    down = _number(down_payment, '頭金')
    period = _years(years)
    if price <= 0 or not 0 <= down <= price:
        raise AppError('INVALID_MORTGAGE_AMOUNT', '頭金は公開済み物件価格以下で入力してください。')
    principal = price - down
    if not boundaries['years_min'] <= period <= boundaries['years_max']:
        raise AppError('RATE_YEARS_OUTSIDE', '返済期間が選択した参考金利の適用範囲外です。')
    if not boundaries['loan_amount_min'] <= principal <= boundaries['loan_amount_max']:
        raise AppError('RATE_AMOUNT_OUTSIDE', '借入額が選択した参考金利の適用範囲外です。')
    ltv = principal / price
    max_ltv = rate.get('max_loan_to_value')
    if max_ltv not in ('', None) and ltv > _number(max_ltv, '融資率上限'):
        raise AppError('RATE_LTV_OUTSIDE', '融資率が選択した参考金利の適用範囲外です。')
    selected_rate = rate.get('rate')
    rate_basis = '公開済み参考金利'
    if 'rate_over_90_percent' in rate or 'フラット35' in str(rate.get('product', '')).replace('３５', '35') or rate.get('rate_label', '').find('9割以下') >= 0:
        if ltv > Decimal('0.9'):
            if rate.get('rate_over_90_percent') in ('', None):
                raise AppError('RATE_LTV_UNCONFIRMED', '融資率9割超の金利が未確認です。スタッフにご確認ください。', 409)
            selected_rate = rate['rate_over_90_percent']
            rate_basis = '融資率9割超の公開済み参考金利'
        else:
            rate_basis = '融資率9割以下の公開済み参考金利'
    result = calculate_mortgage(price, down, principal, selected_rate, period)
    references = [rate['reference']] if rate.get('reference') else []
    if not references and rate.get('source_url'):
        references = [{'source_url': rate['source_url'], 'filename': rate.get('source_name', '確認・公開済み参考金利')}]
    price_reference = snapshot.get('property', {}).get('field_references', {}).get('price')
    if price_reference and price_reference not in references:
        references.append(price_reference)
    result.update(
        bank=rate.get('bank'), product=rate.get('product'), rate_type=rate.get('rate_type'),
        rate_id=rate_id, rate_basis=rate_basis, loan_to_value=float(ltv),
        loan_to_value_percent=float(ltv * 100), effective_date=start.isoformat(),
        valid_until=end.isoformat(), conditions=rate.get('conditions', []),
        product_notes=rate.get('notes', ''), references=references,
        version=snapshot['version'], notes=CALCULATION_NOTES + ' ' + str(rate.get('notes', '')),
    )
    return result


def calculate_explicit_loan(snapshot, loan_amount, years, rate_id, property_price=None):
    matches=[r for r in snapshot.get('rates',[]) if r.get('id')==rate_id]
    if len(matches)!=1: raise AppError('RATE_NOT_FOUND','公開参考金利の商品を確認してください。',404)
    rate=matches[0];start,end=_rate_dates(rate);bounds=_boundaries(rate)
    principal=_number(loan_amount,'借入額');period=_years(years)
    if not bounds['years_min']<=period<=bounds['years_max']: raise AppError('RATE_YEARS_OUTSIDE','商品の返済期間外です。')
    if not bounds['loan_amount_min']<=principal<=bounds['loan_amount_max']: raise AppError('RATE_AMOUNT_OUTSIDE','商品の借入額範囲外です。')
    requires_price='rate_over_90_percent' in rate or rate.get('max_loan_to_value') not in (None,'') or 'フラット35' in rate.get('product','')
    if requires_price and property_price is None: raise AppError('PROPERTY_PRICE_REQUIRED','この商品は融資率の確認が必要です。対象住宅の取得価格を教えてください。',409)
    if property_price is not None:
        price=_number(property_price,'顧客申告取得価格')
        if price<principal: raise AppError('INVALID_MORTGAGE_AMOUNT','取得価格と借入額を確認してください。')
        explicit=dict(snapshot,property={'price':float(price)})
        result=calculate_from_snapshot(explicit,float(price-principal),period,rate_id)
        result.update(price_basis='顧客申告取得価格（物件資料との照合未実施）',property_context=None)
        return result
    result=calculate_mortgage(principal,0,principal,rate['rate'],period)
    result.update(property_price=None,down_payment=None,rate_id=rate_id,bank=rate['bank'],product=rate['product'],rate_type=rate['rate_type'],effective_date=start.isoformat(),valid_until=end.isoformat(),references=[rate['reference']],version=snapshot['version'],property_context=None,price_basis='物件未選択・顧客申告借入額',product_notes=rate['notes'],notes=CALCULATION_NOTES+' '+rate['notes'])
    return result
