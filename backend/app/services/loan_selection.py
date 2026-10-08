"""Require a customer's explicit published-product choice before AI calculation.

This intentionally recognizes a small selection grammar, not general intent.
Assistant statements and tool arguments cannot establish customer consent.
"""
import re
import unicodedata

from app.models.domain import AppError


def _normalize(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(value)).casefold())


def _aliases(rate):
    aliases = {_normalize(rate.get(key, '')) for key in ('bank', 'product', 'rate_type')}
    bank = _normalize(rate.get('bank', ''))
    product = _normalize(rate.get('product', ''))
    rate_type = _normalize(rate.get('rate_type', ''))
    # Abbreviations are available only when their published label establishes them.
    if '三菱ufj' in bank:
        aliases.update(('三菱ufj', '三菱ufj銀行', 'ufj', 'ufj銀行', 'mufg'))
    if 'フラット35' in product or 'flat35' in product:
        aliases.update(('フラット35', 'flat35'))
    if '変動' in rate_type:
        aliases.update(('変動', '変動金利'))
    if '固定' in rate_type:
        aliases.update(('固定', '固定金利'))
    if '全期間固定' in rate_type:
        aliases.update(('全期間固定', '全期間固定金利'))
    return aliases - {''}


_PREFIX = re.compile(r'^(?:(?:金利|商品|金利商品|参考金利|住宅ローン|ローン|希望|希望する商品|計算)は|選ぶのは|使うのは|今回は|やっぱり|それなら|では)*')
_CHOICE = re.compile(
    r'^(?:の|と|または|か|も)*('
    r'|です|で'
    r'|で(?:お願いします|お願いいたします|計算(?:して|してください|お願いします)|試算(?:して|してください|お願いします))'
    r'|を?(?:選びます|選びました|選択します|希望します|希望です|使います)'
    r'|に(?:します|したいです|してください|変更します|変更してください)'
    r'|を(?:使って|選んで)(?:計算|試算)(?:してください|お願いします)'
    r')$'
)
_REFUSAL = re.compile(r'ではなく|じゃなく|ではない|じゃない|(?:は|を)(?:使わ|選ば)|選びません|選んでいません|選んでません|希望しません|希望しない|使いません|使いたくない|選びたくない|やめ(?:ます|たい|て)|不要|取り消|キャンセル')
_RESET = re.compile(r'未定|まだ(?:選|決め)|決めていません|どの商品も選ば|おすすめで|お任せで|どちらでも|どれでも|別の商品に変更')
_QUESTION = re.compile(r'[?？]|とは|について|どちら|どれ|何です|どう|教えて|説明して|ますか|ですか|でしょうか|か$')


def require_selected_rate(snapshot, events, rate_id):
    """Raise RATE_CONFIRMATION_REQUIRED unless the latest choice matches rate_id.

    Events must be Store.events() records in their chronological order. Unknown
    rate IDs remain the mortgage calculator's RATE_NOT_FOUND responsibility.
    """
    rates = snapshot.get('rates', [])
    if not any(rate.get('id') == rate_id for rate in rates):
        return
    alias_ids = {}
    for rate in rates:
        for alias in _aliases(rate):
            alias_ids.setdefault(alias, set()).add(rate['id'])
    pattern = re.compile('|'.join(re.escape(alias) for alias in sorted(alias_ids, key=len, reverse=True)) or r'(?!)')
    selected = None
    for event in events:
        if event.get('kind') != 'message' or event.get('role') != 'user' or event.get('channel') not in {'text', 'voice'}:
            continue
        text = _normalize(event.get('text', ''))
        candidates = set()
        mentions = set()
        refused = set()
        for clause in re.split(r'[、,。.!！;；\n]+', text):
            if _RESET.search(clause) and not (re.search(r'物件|購入対象|号地',clause) and not re.search(r'商品|金利',clause)):
                selected = None
                continue
            matches = list(pattern.finditer(clause))
            ids = set().union(*(alias_ids[match.group()] for match in matches)) if matches else set()
            if _REFUSAL.search(clause):
                refused.update(ids)
                # A generic refusal also revokes an earlier product choice.
                if not ids:
                    selected = None
                continue
            if not matches or _QUESTION.search(clause):
                mentions.update(ids)
                continue
            # Parenthetical published product qualifiers do not change a choice.
            # Safety checks above still see refusals/questions inside them.
            clause = re.sub(r'\([^()]*\)', '', clause)
            matches = list(pattern.finditer(clause))
            ids = set().union(*(alias_ids[match.group()] for match in matches)) if matches else set()
            mentions.update(ids)
            residual = _PREFIX.sub('', pattern.sub('', clause))
            residual = re.sub(r'[「」『』\"\']', '', residual)
            if residual in {'と', 'または', 'か', 'も', 'の'}:
                continue
            if _CHOICE.fullmatch(residual):
                candidates.update(ids)
        if refused and (selected in refused or candidates):
            selected = None
        elif candidates:
            # Multiple products in a selection utterance require clarification.
            selected = next(iter(candidates)) if len(candidates) == 1 and len(mentions) == 1 else None
    if selected != rate_id:
        products = '、'.join(dict.fromkeys(str(rate.get('product') or rate.get('bank') or rate['id']) for rate in rates))
        raise AppError('RATE_CONFIRMATION_REQUIRED', f'どの参考金利商品を使うか、商品名を明示してください（公開商品: {products}）。', 409)
