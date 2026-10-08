# SANZO Demo用資料

公開情報を基にSANZOがデモ用に再構成した資料です。第三者の写真、平面図、バナー、紙面デザインを転載していません。

| ファイル | 内容 | 対象 |
| --- | --- | --- |
| `demo_documents/物件概要_demo.pdf` | 価格、住所、面積、完成年月、間取りの根拠、情報期限 | コモンステージ八千代中央 分譲住宅 No.15 |
| `demo_documents/設備仕様_demo.pdf` | No.15に掲載された15項目の設備・性能情報 | 同じNo.15 |
| `demo_documents/周辺環境_demo.pdf` | 駅と周辺施設の公式掲載範囲 | 販売中4戸の距離範囲・最長値。No.15単独値ではない |
| `demo_documents/住宅ローン_demo.xlsx` | 2商品の参考金利、期間、審査条件、出典 | 2026年10月借入／資金受取分 |

これらのファイルの生成・SDK読取だけでは、管理者確認や公開は完了しません。管理画面でSDK結果と業務上の対応関係を確認し、確認・公開してください。

## 出典と基準日

確認日は2026-10-07（Asia/Tokyo、日付精度）です。詳細な出典と確認範囲は `research/SOURCE_MANIFEST.md` と `research/public_data.json` に保存しています。

- 積水ハウスのNo.15情報：情報登録日2026-10-02、有効期限2026-10-15。価格は土地建物価格（税込）76,900,000円。
- 駅までの最長徒歩12分、距離920〜950mは販売中4戸の掲載範囲です。No.15単独の徒歩分数を構造化値として登録していません。
- 間取り3LDKはNo.15の公式平面図の室名からの分類です。ページの文字欄に明記された間取りではありません。
- 駐車可能台数は未確認です。公式図面の2台描写から「2台駐車可」と断定していません。
- 蓄電システムの公式容量表記「4.9kW」を保持しています。kWhへの訂正は行っていません。
- 周辺ページ固有の情報更新日は未記載です。写真撮影年月2025年8月を情報更新日として扱っていません。
- 三菱UFJ銀行：変動参考年利1.195%、2026年10月借入分。優遇コースの適用条件・銀行審査があります。
- フラット35：新機構団信付き、21〜35年、融資率9割以下の最頻参考年利3.83%。9割超は参考3.94%。取扱金融機関ごとの金利、審査条件、手数料を保証しません。
- 金利の期間開始日2026-10-01は月次表示の正規化です。公表日を特定したものではありません。有効期限は2026-10-31です。

期限後は現行の確定情報として使用せず、実演前に販売状況・価格・金利を再確認してください。

## 生成方法

```bash
backend/.venv/bin/python scripts/generate_documents.py --smoke
backend/.venv/bin/python scripts/generate_documents.py --research research/public_data.json
```

PDFはReportLabによるネイティブ文字PDFです。フォントはGoogle FontsのNoto Sans JPをSIL Open Font Licenseで使用し、400ウェイトの静的インスタンスを埋め込んでいます。フォントとライセンスは `assets/fonts/` にあります。

Excelは `@oai/artifact-tool` の公開APIで作成しています。生成時はCodexのバンドルNodeとArtifact Toolが必要です。運用時のDemo起動や資料アップロードには生成用のArtifact Toolは不要です。

`Rates` シートの第1行がヘッダーです。金利は年利％の数値（1.195は1.195％）、日付はExcelの日付値として格納します。融資率9割超の金利、年数、融資額、最大融資率の条件を独立列で保持しています。月額返済の計算はBackendが行います。

PDFの英語キーと値は取込時の対応関係を確認しやすくするための表示です。`equipment:` と `surroundings:` は複数行存在します。

## 生成物の検証

- 3つの業務PDFは各1ページ。PopplerでPNGへ描画し、全ページを目視しました。
- 住宅ローンExcelはArtifact Toolで値・日付・条件列を確認し、データ範囲と案内範囲を描画して目視しました。
- 描画証跡は `evidence/documents/`、ファイルSHA-256は `evidence/documents/artifacts.json` に保存しています。
- 生成処理には文書パーサーを使用していません。Demo取込時の解析はDocumentSdkAdapterからSANZO配布SDKを使用します。
- Microsoft Excelのネイティブアプリ上での表示は未検証です。このWorkbookには計算式を持たせていません。

Smoke用 `demo_documents/smoke/minimal.pdf` と `minimal.xlsx` はSDK確認専用の架空入力です。実物件の業務資料として公開しないでください。

## 会社接客員への定位修正で追加した共通FAQ

- `住宅購入基礎FAQ_demo.pdf`: 国土交通省の一般購入・重要事項説明・現地確認・仲介手数料の要約。
- `住宅ローン基礎FAQ_demo.pdf`: 住宅金融支援機構のFlat35基本特徴・新築購入手続・検査と審査の違い。
- どちらも `knowledge_scope: general`。特定物件や会社のサービスを意味しません。会社資料は未登録です。
- 確認/基準日2026-10-07、Demo再確認期限2026-11-06。公式公表日や制度失効日とは区別。
- 出典の詳細は `research/consultation_sources.json`、確認表は [CONSULTATION_POSITIONING](CONSULTATION_POSITIONING.md)。正常6件はSDK解析まで準備済みで、管理者確認・公開は未実施。
- PDF2件はPopplerで全ページ描画・目視済み（各1ページ）。SDK解析の raw・標準化は正常Adminに保存。
- 再生成スクリプトは `scripts/generate_consultation_documents.py`。生成・調査は業務確認や公開の代用になりません。準備済みファイルを再生成・重複登録する必要はありません。
