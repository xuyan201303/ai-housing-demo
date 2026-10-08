import re

HANDOFF_MESSAGE = '住宅ローン審査の可否についてAIから確定的なご案内はできません。担当スタッフよりご案内いたします。'


def needs_loan_handoff(text: str) -> bool:
    return bool(re.search(r'ローン|融資|審査', text) and re.search(r'絶対|必ず|通る|通り|通ります|通れ|可否|合否|落ち|大丈夫|審査.*(可能|承認|不承認)', text))


def consultation_policy(session, context, text):
    """Shared text/voice guard for absent facts and ambiguous property questions."""
    if not context['property_selected'] and re.search(r'^(?:価格は|値段は|いくら(?:くらい|ぐらい)?(?:ですか)?[?？。．]*$|多少钱[?？。．]*$|駅から|駅まで|最寄り駅|間取りは|設備は|面積は)', text.strip()):
        return 'どの物件についてのご質問でしょうか。一般的な住宅購入のご相談も、そのままお伺いできます。'
    if not context['company_material_available'] and re.search(r'営業時間|定休日|御社のサービス|貴社のサービス|御社.*保証|御社.*約束', text):
        return '会社のサービス・営業時間について、確認・公開済みの会社資料がまだありません。担当スタッフへご相談ください。'
    if not context['items'] and re.search(r'購入の流れ|購入手続|重要事項|住宅購入.*(?:何から|始め|注意)', text):
        return '住宅購入の共通資料はまだ確認・公開されていません。資料に基づくご案内は担当スタッフへご相談ください。'
    return None
