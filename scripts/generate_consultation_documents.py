"""Small, source-grounded FAQ documents; never confirm or publish them."""
from pathlib import Path
import json
from generate_documents import business_pdf
ROOT = Path(__file__).resolve().parents[1]
DATE='2026-10-07'
EXPIRY='2026-11-06'
SOURCES=[
 {'filename':'住宅購入基礎FAQ_demo.pdf','title':'住宅購入の基礎 FAQ','source_name':'国土交通省：消費者向け不動産取引のお知らせ','source_url':'https://www.mlit.go.jp/totikensangyo/const/1_6_bf_000013.html','scope_notes':'日本の住宅購入に関する一般情報。会社の対応・個別契約・特定物件の条件ではありません。','faq':[
 ('住宅購入は何から始めればよいですか？','まず希望条件を整理し、購入候補の資料と現地の状況を確認しましょう。国土交通省は取引の流れを例として示し、実際の流れは契約相手や仲介業者へ確認するよう案内しています。この会社固有の購入手順は、会社資料の確認後にご案内します。'),
 ('重要事項説明とは何ですか？','購入予定の物件について知っておくべき重要な事項を、不動産業者から説明してもらう手続です。対面のほかオンラインで受ける方法もあります。利用方法は取引を担当する業者へ確認してください。AIの案内で重要事項説明を代行するものではありません。'),
 ('写真やオンライン説明だけで購入を決めてもよいですか？','現地訪問は、画像だけでは判断しづらい物件状況の把握に役立ちます。写真の情報と現地の状況を確認しましょう。この会社の見学受付方法や日時は未登録のためスタッフへ確認してください。'),
 ('仲介手数料は必ずかかりますか？','国土交通省の説明は、仲介で契約が成立した場合の仲介手数料を対象としています。仲介を依頼する際には、定められた上限の範囲で金額を事前に合意することが重要です。この会社の販売形態や手数料の有無は会社資料で未確認です。')
 ]},
 {'filename':'住宅ローン基礎FAQ_demo.pdf','title':'住宅ローンの基礎 FAQ','source_name':'住宅金融支援機構：フラット35・新築住宅購入時の融資手続','source_url':'https://www.flat35.com/loan/lineup/flat35/flow_shinchiku.html','scope_notes':'日本のフラット35による新築住宅購入の一般説明。他商品へ条件を転用しません。','faq':[
 ('フラット35はどのような住宅ローンですか？','民間金融機関と住宅金融支援機構が提携する、最長35年の全期間固定金利の住宅ローンです。借入時に返済終了までの金利が確定します。対象住宅や申込条件の確認が必要です。金利の具体的な数値は別の確認・公開済み参考金利資料を使います。'),
 ('新築住宅でフラット35を利用する手続は？','取扱金融機関へ借入れを申し込み、金融機関から審査結果の連絡を受けます。対象住宅の検査・適合証明の手続もあります。物件検査に合格しても融資審査の承認は保証されません。実際の必要書類や手続は取扱金融機関へ確認してください。'),
 ('住宅の物件検査に合格すればローン審査にも通りますか？','いいえ。住宅金融支援機構は、物件検査に合格しても取扱金融機関または機構の審査により希望に沿えない場合があると案内しています。個別の審査判断は金融機関へ確認してください。AIは合否を断定しません。')
 ]}
]
for s in SOURCES:
 rows=[('knowledge_scope','general'),('source_name',s['source_name']),('source_url',s['source_url']),('checked_at',DATE),('effective_date',DATE),('valid_until',EXPIRY),('scope_notes',s['scope_notes'])]
 if 'ローン' in s['filename']: rows.append(('product_source_url','https://www.flat35.com/loan/lineup/flat35/index.html'))
 for q,a in s['faq']: rows.extend([('faq_question',q),('faq_answer',a)])
 business_pdf(ROOT/'demo_documents'/s['filename'],s['title'],'公式情報の要約 / 管理者確認・公開前の資料',rows,['確認日・基準日はSANZOによる確認日です。公式ページの更新日を推定していません。','有効期限はDemoでの再確認期限です。公式制度の失効日ではありません。管理者が範囲・日付・説明を照合し、確認・公開するまでAIには使用しません。'])
(ROOT/'research/consultation_sources.json').write_text(json.dumps({'checked_at':DATE,'review_deadline':EXPIRY,'official_publication_date':'NOT_STATED','company_materials':'MISSING','documents':SOURCES},ensure_ascii=False,indent=2))
print('Prepared two general FAQ PDFs; confirmation/publication not performed.')
