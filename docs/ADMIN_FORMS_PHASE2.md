# Phase 2 第1輪：社員向け Admin フォーム

対象は既存の資料ごとの候補編集、下書き保存、社員による確認です。資料置換、公開差分、版の復元は次輪の対象です。

## 社員の操作

1. 「資料管理」で PDF / Excel を登録し、「SDK 解析を実行」を押します。
2. 資料を選び、左の業務区分から物件、設備、FAQ、住宅ローンを整理します。SDK が読み取った候補を社員が原資料と照合してください。
3. 「資料用途」と「知識範囲」を別々に確認します。解析成功だけで対客利用が許可されることはありません。
4. 「下書きを保存」で編集内容を Backend に保存します。Chrome を更新して同じ資料を開くと保存内容を復元します。
5. 原資料との照合が完了したら確認メモを記入し、確認チェックを自分で付けて確認操作を行います。
6. 確認後は公開待ちです。「公開管理」で確認済みかつ対客利用可の資料を選び、既存の公開操作を行います。

下書き、業務確認、公開は別の状態です。確認チェックや公開操作は自動実行しません。

## 日常操作の対応項目

| 業務区分 | 対応する既存データ |
|---|---|
| 物件情報 | `property_name`、`lot`、`price`、`address`、`layout`、`land_area`、`building_area`、`station`、`walking_minutes`、`completion_date`、`parking` |
| 設備情報 | `property.equipment` の文字列一覧。追加、編集、削除 |
| FAQ | `faq[].question`、`answer`、`reference.location`、`source_url` と登録元資料。追加、編集、削除 |
| 住宅ローン | `rates[].bank`、`product`、`rate_type`、`rate`、`notes`、既存の借入額・期間・融資率条件、基準日・有効期限・出典。フォームにない `conditions` 等は保持 |
| 資料管理 | アップロード、SDK 解析、資料用途、知識範囲、資料の出典・日付・適用範囲、確認メモ |
| 公開管理 | 既存の資料選択と公開、公開済み資料・版の閲覧 |
| 接客履歴 | 既存の社員向け接客・監査履歴 |

金利・借入条件は原資料に存在する値だけを登録してください。未記載の条件をフォームが自動補完することはありません。

`raw` は SDK の実際の返却結果、`normalized` は既存の標準化結果、`reviewed` は社員の業務確認結果です。手動補録は確認候補の編集であり、SDK が読み取った内容として扱いません。未対応の追加フィールドは保存時に保持します。高度な JSON 編集は通常の物件・設備・FAQ・金利操作では不要です。

任意の顧客 PDF の自動整理を保証するものではありません。対応形式に合わない資料でも、SDK の実際の読み取りを残したまま対応する業務項目を社員が整理します。画像 PDF の OCR など、未実装の解析を成功扱いにしません。

## 用途と範囲

| 内部値 | Admin 表示 |
|---|---|
| `customer` | 顧客への案内に使用可 |
| `internal` | 社内専用 |
| `unclassified` | 未確認 |

知識範囲は `property`（具体物件）、`general`（共通住宅購入知識）、`company`（会社サービス・接客規則）です。用途とは独立に保存します。R1 の Customer 返却境界、R2 の資料承認・AI コンテキスト境界は引き続き適用されます。

## 下書き API

既存の Admin 認証が必要です。Customer に下書き API はありません。

| 操作 | API | 入出力 |
|---|---|---|
| 候補の読込 | `GET /api/admin/documents/{id}/draft` | `document_id`、`document_sha256`、`source_revision`、`base_confirmation_id`、`base_published_version`、`revision`、`reviewed`、`usage`、`note`、`saved_at`、`saved_by`、`confirmed_at`、`stale` |
| 下書き保存 | `POST /api/admin/documents/{id}/draft` | 入力：`document_sha256`、`source_revision`、`revision`、`reviewed`、`usage`、`note`。出力：保存後の候補と新しい revision |
| 明示確認 | `POST /api/admin/documents/{id}/draft/confirm` | 入力：`document_sha256`、`source_revision`、`revision`、`note`。保存候補を明示的に業務確認 |

資料 ID、ファイル内容の SHA-256、元の確認・公開版、候補 revision で下書きを対象資料に結び付けます。別の資料の候補や古い画面からの上書きを拒否します。下書き保存は既存の SDK 結果、確認済み内容、公開版を変更しません。

入力エラーは `error.field_errors` の項目パスと日本語メッセージで返します。例：`rates.0.valid_until` →「金利の有効期限を入力してください。」。画面の該当欄の近くに表示し、別の区分にあるエラーは区分への案内も表示します。

確認操作で既存の R2 確認記録を作成します。新しい確認は既存の R2 承認有効性に従います。公開版の保存内容を上書きする処理や、自動公開はありません。

## 隔離 Chrome 検証

通常の `data/housing.db` にデータベース接続・照会・書込みを行わず、次の専用 TEST 領域を使用します。通常DBファイルは変更がないことを SHA-256 で確認します。

- Admin：`http://localhost:5175/admin`
- Backend：`127.0.0.1:8002`
- DB：`evidence/phase2_admin_forms/ui-test.db`
- Upload：`evidence/phase2_admin_forms/ui-uploads/`
- 起動スクリプト：`scripts/phase2_admin_test_server.py`

Admin の登録・解析・保存・確認・公開は実サービスです。SANZO SDK はインストール済みの 1.8.0 配布物を利用します。Customer の文言検証だけは明示した TEST provider を使用し、実 AI・TTS・マイクロフォン検証ではありません。サーバーと Chrome は外部接続を遮断し、有料 API を呼びません。正常 DB、`.env`、SDK ソース、AI モデル、選定済みの音声設定を変更しません。
