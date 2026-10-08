# Phase 2 第2輪：資料更新・公開 API

全て既存の Admin 認証が必要です。共有 `admin` の実際の操作として記録し、個人社員を推測しません。Customer / Staff の権限や API 契約は変更しません。

## 資料の修訂

| 操作 | API | 主な内容 |
|---|---|---|
| 内容修正を開始 | `POST /api/admin/documents/{id}/revisions` | `reason`。元ファイル・SDK結果を使った独立した業務下書き |
| 修訂一覧 | `GET /api/admin/documents/{id}/revisions` | 資料 ID、確認 ID、修訂 ID、確認時の用途、日時、実際の確認者、公開版、取消状態 |
| 下書き読込・保存・確認 | 既存の `/draft`、`/draft/confirm` | ファイルハッシュ、元状態ハッシュ、下書き revision を引き続き照合 |
| 未公開更新の取消 | `POST /api/admin/documents/{id}/updates/cancel` | 元の公開資料・SDK証拠・公開履歴を削除しない |
| 同内容の検索 | `GET /api/admin/documents/duplicates?sha256=...` | 内容ハッシュが同じ既存資料を表示 |
| 新ファイル登録 | `POST /api/admin/documents` | multipart `file`、`duplicate_action=check/reuse/separate`、必要なら `reuse_document_id` |
| 差し替え登録 | 同じ登録 API | 明示した `replaces_document_id` と `replaces_confirmation_id` を付ける。ファイル名では判定しない |

新しいファイルは別 ID で登録・SDK解析・社員確認します。`reuse` は既存資料を返すだけで、既存の確認・用途や公開版を変更しません。`separate` で保存した資料も未確認から始まります。

普通の内容修訂は、旧公開版が参照する確認を失効させません。資料用途を明示変更する既存 `/usage` は独立した撤回操作です。撤回の境界を越えた古い確認を、再許可・復元によって復活させません。

## 公開草案・差分・公開

| 操作 | API | 入出力 |
|---|---|---|
| 草案一覧 | `GET /api/admin/publication-drafts` | 保存済み草案と状態 |
| 現行版から作成 | `POST /api/admin/publication-drafts` | `{}`。現行版の資料 ID と確認 ID を基線として保持 |
| 履歴から復元草案 | `POST /api/admin/versions/{version}/restore-draft` | 現行版を基線とし、選択した履歴の資料・確認を候補にする |
| 草案読込 | `GET /api/admin/publication-drafts/{id}` | `id/revision/base_version/items/note/state`、保存・確認情報 |
| 草案保存 | `POST /api/admin/publication-drafts/{id}` | `revision/items/note`。items は `document_id/confirmation_id`、差し替えは元の資料・確認 ID も明示 |
| 差分確認 | `POST /api/admin/publication-drafts/{id}/preview` | 基準版、追加・維持・差し替え・除外、業務項目の変更前後、能力、警告、公開不可理由、`preview_token` |
| 最終公開 | `POST /api/admin/publish` | `draft_id/draft_revision/preview_token/idempotency_key` |
| 版履歴 | `GET /api/admin/versions` | 元の全履歴に、新規公開時の実際の操作者・変更説明・修訂関連を追加 |

`items` は次版の全資料集合です。画面では現行版の集合を先に読込み、社員が追加・差し替え・除外します。未編集の旧承認を、自動的に最新の確認や未確認下書きへ置き換えません。

最終公開は一つの SQLite トランザクションで、基準版・草案版・明示確認・用途・日付・内容の競合を再検証します。プレビュー後に基準版や承認状態が変われば再確認が必要です。同一の `idempotency_key` と同一の送信内容は同じ公開版を返し、二重に版を作りません。失敗した送信には公開版も成功記録も残しません。

旧形式の `{"document_ids":[...]}` による Admin 公開は `409 PUBLICATION_PREVIEW_REQUIRED` です。プレビューを経由しない別の Admin 公開ルートはありません。警告と公開不可理由は分離し、例えば有効金利が無いことは試算不可の警告として表示します。

定型資料の明確な `price:` 数値行と登録価格が異なる場合も、プレビューと最終公開を止めます。本文を原資料と照合するか、更新済みの新しいファイルに差し替えてください。登録欄だけの変更によって SDK 原文が書き換わることはありません。この限定的な検査で、自由な日本語本文や表に含まれる全ての意味上の矛盾を検出できるわけではありません。

公開版は固定された資料・確認の組み合わせです。新接客は新しい版、有効で撤回されていない既存接客は開始時の版を使います。復元も再検証と明示公開を経て新しい版を作り、過去の版・確認・原ファイルを上書きしません。

## 環境と限界

新規管理用テーブルは `document_revisions`、`publication_drafts`、`publication_submissions`。本輪では隔離 TEST DB でのみ初期化・実測しました。正常 DB にこの構造を適用する手順は [正常環境の後続更新手順](DOCUMENT_UPDATE_NORMAL_UPGRADE.md) に分けています。

本輪は公開資料の改訂・確認・公開の管理です。社員個別アカウント、複雑な承認フロー、PDFの視覚比較、任意資料の自動正規化、実AI・音声・通常環境の受入れを完了した意味にはなりません。
