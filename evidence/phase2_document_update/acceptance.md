# HOUSING_V1_DOCUMENT_UPDATE_AND_PUBLISH

2026-10-08、Phase 2 第2輪の隔離実装・検証完了。通常環境への適用は未実行。

社員は「更新理由」→登録内容の修正、または新ファイルへの差し替え→SDK実解析・照合→下書き保存→明示確認→現行版から公開草案→差分確認→公開の順で、一つの資料だけを更新できます。他の有効な資料と、未撤回の既存接客の版は保持します。

## 環境と証拠の種類

- 実際の Google Chrome、`cua_repl` native AX による操作。画面は [index.html](index.html)、操作状態は [ui_observations.json](ui_observations.json) と各 `.ax.txt`。
- Admin：<http://localhost:5176/admin>、Customer：<http://localhost:5176/>、Staff：<http://localhost:5176/staff>。Frontend 5176 → Backend 8003、専用 `ui-test.db` / `ui-uploads/`。
- 六つの既存サンプル PDF / XLSX と新しい TEST PDF、計7資料を導入済み SDK 1.8.0 で実解析。TEST PDF の77,900,000円、追加金利条件、Excel資料単位の手動メタデータは検証用の人工入力。SDK認識結果と混同していない。[SDK記録](sdk_parse_records.json)、[差し替え証拠](replacement_sdk_proof.json)、[手動整理記録](loan_metadata_manual_test.json)。
- 初期 v1 の六資料確認・公開は明示した隔離 HTTP セットアップ。v2 の更新・公開、v1内容を基にした新規 v3 の復元公開は実Chrome。v1設定をChrome操作と称していない。
- Backend回帰のHTTP操作は隔離FastAPI TestClientの実際のルートとSQLite取引を使用します。8003の実ネットワーク応答を読み返した証拠、Chrome操作、TestClient回帰を区別し、ネットワーク切断や二窓同時クリックを実測したと称しません。
- AI回答文のみ明示した TEST provider。Tools、資料、Backend計算、Staff、Sessionは実装本体。外部接続を拒否、AI/TTS資格情報はTESTプロセス内で無効化。付費AI/TTS呼出0、マイク未使用。

## 実際の検証

| 項目 | 結果・検証方法 | 主な証拠 |
|---|---|---|
| A：conditions | Chromeで追加3行・編集・1行削除・保存・刷新復元・明示確認。2行の順序、notes、数値条件、未編集値を保持。未知拡張保持はBackend HTTP回帰。 | [01](01-conditions-restored.png)、[02](02-confirmation-flow.png)、[確認API](conditions_confirmation_api.json) |
| B：更新準備はv1を維持 | ChromeでTEST価格改訂を保存・確認。旧Chrome接客と別の新規HTTP接客は公開前もv1の完全な情報を使用。未公開更新の取消でもv1を保持。 | [04](04-confirmed-update-v1-retained.png)、[05](05-old-session-after-confirm.png)、[新接客読回](new_session_before_publish.json) |
| C：一資料だけ差し替え | 新PDFを旧資料ID・確認IDへ明示関連付け、実SDK解析・確認。現行6資料の草案を刷新復元。差分は差し替え1・維持5、設備・周辺・2FAQ・金利を保持。 | [06](06-new-file-update-entry.png)、[07](07-sdk-replacement-reviewed.png)、[08](08-v2-publication-diff.png)、[v2読回](v2_readback.json) |
| D：新旧接客の版固定 | Chrome明示公開後、新接客v2はTEST価格77,900,000円。旧接客は再度Tools取得してv1・76,900,000円を保持。 | [09](09-v2-published.png)、[10](10-old-v1-after-v2.png)、[11](11-new-customer-v2.png) |
| E：用途撤回 | 実際の隔離Admin/Customer HTTP回帰で、明示撤回は旧・新接客及び復元に即時制限。再許可だけで古い承認を復活させない。Chromeでの撤回を実施したとは称していない。 | `backend_tests.log`、`test_restore_revocation_dates_and_internal_approval_are_blockers`、`test_knowledge_boundary.py` |
| F：重複・不適格 | 実際の隔離HTTPでSHA-256重複、明示reuse/separate、未確認、internal、期限切れ、承認不足、登録内容競合を検査。勝手な上書き・権限付与なし。 | `test_duplicate_upload_explicit_identity_and_cancel_leave_v1`、`test_restore_revocation_dates_and_internal_approval_are_blockers` |
| G：競合・再送 | 異なる草案と古いrevisionを使う隔離HTTPで、基準版変更・旧プレビュー・承認変更を拒否。同一idempotency再送は同じ版を返す。二つのChrome画面での同時クリック実測とは区別。 | `test_publication_updates.py::test_stale_draft_parallel_publish_and_changed_approval_require_new_preview`、`test_real_sdk_collection_one_revision_preserves_other_sources_and_restore`、[取引回帰](transaction_rollback_regression.json) |
| H：復元は新しい版 | Chrome履歴→v1復元草案→保存→最終Backendで再プレビュー。77,900,000円→76,900,000円を表示し、明示公開でv3新規作成。v1/v2の全体ハッシュ及び7資料SDK raw/normalizedを保持。 | [15](15-restore-preview.png)、[16](16-restored-v3.png)、[17](17-history-v1-v2-v3.png)、[最終読回](final_readback.json) |
| I：取消・失敗 | Chromeで未公開更新を取消しv1が継続。隔離TestClientの実SQLite取引で後段の公開受付記録保存に故意の失敗を起こし、全体rollback及び同じ再送keyによる回復を確認。 | `business-update-cancelled.ax.txt`、[取引回帰](transaction_rollback_regression.json)、`test_update_permission_edges.py::test_failure_at_publication_receipt_rolls_back_version_and_is_retryable`、`backend_tests.log` |
| J：既存業務 | Chrome一般相談→紹介→明示物件選択→設備・周辺カード→閉じる→v2貸付試算→Staff pending/accepted/completed同期→接客終了。R1/R2及び関連Backend回帰222 PASS、Frontend TypeScript/Vite build PASS。 | [12](12-v2-backend-mortgage.png)、[13](13-staff-accepted-customer.png)、`v2-backend-mortgage-result.ax.txt`、`v2-session-ended.ax.txt`、`backend_tests.log`、`frontend_build.log` |

貸付は選択した三菱UFJ商品・年1.195%・頭金500万円・35年、TEST価格77,900,000円、借入72,900,000円によりBackendが月額212,478円を返しました。条件、基準日、有効期限、免責を表示。これは計算・版保持の動作証拠であり、実際の融資条件や審査可否の証明ではありません。

現在のTEST公開版はv3、承認付き資料6件。新規一般接客は物件未選択、明示選択後にv3の76,900,000円・設備・周辺・2商品を返し、このHTTP確認用Sessionは終了済み。[最終読回](final_readback.json)。

## 発見と最小修正

1. 新確認で旧公開承認が無効になる不具合を実SDK隔離データで再現。独立した不可変確認関連と用途撤回epochを導入し、更新準備と明示撤回を分離。[元の再現](bug_reproduction.json)。
2. 登録価格だけの変更と承認本文の明示的な `price: 数字` の不一致を検出。プレビュー・最終公開共通で阻止し、SDK原文を書き換えない。[修正記録](manual_revision_source_conflict_fix.json)。
3. 別ファイルIDを含む復元の初回Chromeプレビューで主要価格差分が欠落。[初回失敗画面](15-initial-restore-missing-price.png)を保存。公開集合の主要項目前後比較を追加し、最終Backend再起動後の実Chrome再プレビューとv3公開で再検証済み。資料identityによる追加/除外/維持の分類は保持。[修正後](15-restore-preview.png)。

`publication_tests.log` は途中の失敗記録として保存した履歴です。現在の結果は最終 `backend_tests.log` の222 PASSです。既存Starlette非推奨警告1件は失敗扱いせず、依存更新は実施していません。

## 変更していない範囲・限界

通常 `data/housing.db` にSQL接続していない。通常DB本体/WAL/SHM、`.env`、SDK配布物・環境・音声設定等65受保護ファイルの前後ハッシュ一致。追加の前輪保護対象は許可された `knowledge_access.py` 以外23件不変。[保護検査](protected_check.json)。通常資料の移行・確認・公開・取消、SDKソースアクセス、モデル/音声変更なし。

任意PDFの自動整理、任意文言の意味矛盾検出、実AI/Realtime/マイク/スピーカー、日本語自然度、通常5173の交付、本番環境は本輪の検証範囲外です。公開差分は主要業務項目と資料本文単位であり、PDF視覚・文字単位の差分ではありません。

次はPhase 2第3輪の完全なAdmin受入れ。通常環境の更新は[後続手順](../../docs/DOCUMENT_UPDATE_NORMAL_UPGRADE.md)を社員の許可後に実施する別作業です。本輪でPhase 3・多物件・音声変更を開始しません。
