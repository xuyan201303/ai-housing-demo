# 建売住宅販売向け AI接客Demo

1つの実在建売住宅で、**PDF / Excel取込 → SANZO SDK解析 → 管理者確認 → 公開版 → 日本語接客 → 住宅ローン概算 → スタッフ引継ぎ**を実装する独立ローカルDemoです。

対象は積水ハウス「コモンステージ八千代中央 分譲住宅 No.15」。公開事実をSANZOが自前の資料に再構成しています。SDK読取と管理者の業務確認は別の工程です。

正常Demoの4資料は実アップロード・SDK解析まで準備済みです。現在の確認数・公開版は [正常環境の準備記録](evidence/normal_demo_preparation.md) を参照してください。利用者がAdminで確認・公開した後、正常5173で物理マイク・スピーカーを受け入れます。[最短の人工操作手順](docs/NORMAL_DEMO_HANDOFF.md)。

**OpenAI API Key設定を反映し、実Responses文字回答とChrome WebRTC経由の実Realtime音声を検証しています。** 音声入力は明示した日本語テスト音源で、物理マイク・スピーカーの現場受入れは未検証です。SDK取込・確認・公開、Backend計算、Staff通知も実測済みです。最新の結果と過去の修正前記録は [acceptance記録](evidence/acceptance.md) が正本です。

## 構成

| 部分 | 実装 |
| --- | --- |
| Frontend | React 19 / TypeScript / Vite、PC優先Responsive、軽量2D Avatar |
| Backend | Python 3.12 / FastAPI、単一プロセス |
| 保存 | SQLite、プロジェクト内の受控アップロードディレクトリ |
| 解析 | 配布wheelのSANZO `document_sdk` 公開API、独立Adapter経由 |
| 文字接客 | OpenAI Responses API、公開版だけを取得するBackend Tools |
| 音声接客 | OpenAI Realtime API / WebRTC、Backend sidebandでTool制御 |
| 状態同期 | Customer / Staffの2秒ポーリング |

入口は `/` 接客、`/admin` 管理、`/staff` スタッフ。多店舗、Multi Tenant、CRM・基幹連携、正式融資審査、3D、正式HAは含みません。

```text
frontend/src/       Customer / Admin / Staff / Voice / Avatar
backend/app/       api / models / schemas / services / repositories
backend/tests/     SDK実入力・業務制御・計算・API・音声制御のテスト
demo_documents/    自有業務PDF3件・住宅ローンExcel1件
research/          公式出典と調査事実（自動公開しない）
data/ uploads/     実行時DB・原本（Git対象外）
evidence/          SDK、HTTP、描画、acceptance記録
```

## 起動

このMacではBackend独立venvとFrontend依存関係を準備済みです。プロジェクトルートで実行します。

```bash
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

別ターミナル：

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Chromeで開きます。

- [接客](http://localhost:5173/)
- [管理](http://localhost:5173/admin)（ユーザー名 `admin`）
- [スタッフ](http://localhost:5173/staff)（ユーザー名 `staff`）

Frontendの `/api` はViteから `127.0.0.1:8000` にproxyします。DBテーブルはBackend起動時に自動初期化します。起動による資料取込・確認・公開はありません。通常DBとテストDBは別です。

ローカル `.env` は作成済みです。パスワードはそのファイルの `ADMIN_PASSWORD` / `STAFF_PASSWORD` で確認してください。README・ログ・ブラウザーへ値を転載しません。Key変更後はBackendを再起動します。

## 新規環境のセットアップ

SDK配布メタデータは **Python >=3.12,<3.13** を要求します。このMacの実測はPython **3.12.13**、Node **24.18.0**、npm **11.16.0**。Python本体は `backend/.python/cpython-3.12.13-macos-aarch64-none/bin/python3.12`、venvは `backend/.venv` です。

既存venvと `.env` を保持してください。新しいチェックアウトではPython 3.12を用意し、次を実行します。

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install --upgrade pip
backend/.venv/bin/python -m pip install -r backend/requirements.txt
cp -n .env.example .env
cd frontend
npm ci
```

`backend/requirements.txt` は検証した依存バージョンと実在wheelの絶対パスを記録しています。配布元は **/Users/kyoen/Projects/sdk**。依存取得にはネットワークが必要です。別マシンでは正式配布wheelの所在だけを修正し、対応Python / OS / CPUの依存を再検証してください。SDKソースrepoへの切替は行いません。

## SANZO SDKとSmoke Test

実在配布物：

- `document_processing_sdk-1.8.0-py3-none-any.whl`（使用）
- `document_processing_sdk-1.8.0.tar.gz`（未使用）
- `DOCUMENT_PROCESSING_SDK_VENDOR_1.8.0_287914d4e000.zip`
- 同ZIPの `.sha256`

ZIP checksumに合格し、ZIP内wheelと単体wheelのSHA-256一致を確認しています。wheel SHA-256は `d791e0602ef138f50a065cd4cc5d3dca801226822b74328230f2faa2c0c75666`。記録は [checksum.json](evidence/sdk/checksum.json)。

配布物確認：

```bash
ls -lah /Users/kyoen/Projects/sdk
cd /Users/kyoen/Projects/sdk
shasum -a 256 -c DOCUMENT_PROCESSING_SDK_VENDOR_1.8.0_287914d4e000.zip.sha256
```

プロジェクトルートへ戻り、PDF / Excelの実在extrasを付けて設置・確認します。requirementsによる設置も同じwheelとextrasです。

```bash
backend/.venv/bin/python -m pip install '/Users/kyoen/Projects/sdk/document_processing_sdk-1.8.0-py3-none-any.whl[pdf,excel]'
backend/.venv/bin/python -c 'import document_sdk; print(document_sdk.__file__)'
backend/.venv/bin/python scripts/sdk_smoke.py
```

確認済みimport元は `backend/.venv/lib/python3.12/site-packages/document_sdk/__init__.py`、版は **1.8.0**。SDKソースrepo、editable install、SDKソースを指すPYTHONPATH、private API、別パーサーfallbackは使用しません。

| 実際の公開API | 入出力・用途 |
| --- | --- |
| `document_sdk.pdf.extract_native_text(Path, limits=...)` | native-text PDF → `Document`、ページ・text_blocks |
| `document_sdk.excel.inspect_workbook(Path, package_limits=...)` | → `WorkbookInspection`、実在シート名 |
| `document_sdk.excel.read_sheet(Path, sheet_name, max_cells=..., formula_view='both')` | → `WorksheetData`、セル座標・値・式情報 |
| `document_sdk.core.DocumentSdkError` | SDK例外の公開基底、Adapterで業務エラーへ変換 |

PDF / Excelの最小入力はいずれも **PASS**、エラーなし。実API署名、戻り値キー、import元は [installation.json](evidence/sdk/installation.json)、[smoke_result.json](evidence/sdk/smoke_result.json)、rawは [smoke_raw.json](evidence/sdk/smoke_raw.json)。`demo_documents/smoke/minimal.*` は架空Smoke入力で、正式Demoでは公開できません。

## 環境変数

ルート `.env` を読込み、実値はGit対象外です。テンプレートは [.env.example](.env.example)。

| 変数 | 用途・初期値 |
| --- | --- |
| `OPENAI_API_KEY` | Backendだけで使用。未設定のAI文字・音声は503 |
| `OPENAI_TEXT_MODEL` | `gpt-4.1-mini`。当該アカウントで実Responses接続を確認済み |
| `OPENAI_REALTIME_MODEL` | `gpt-realtime-2.1`。当該アカウントで実WebRTC音声応答を確認済み |
| `DATABASE_URL` | `sqlite:///./data/housing.db`。SQLiteのみ |
| `UPLOAD_DIR` | `./uploads`。DB・アップロード先はプロジェクト内に制限 |
| `DEMO_MODE` | `demo` / `test`。どちらもAI/SDK mock成功を有効にしない |
| `ADMIN_PASSWORD` | `admin` のBasic認証用。空なら管理操作を拒否 |
| `STAFF_PASSWORD` | `staff` のBasic認証用。別パスワードを設定 |
| `FRONTEND_ORIGIN` | `http://localhost:5173`。許可Frontend origin |
| `MAX_UPLOAD_MB` | 10。設定上限20MB、PDF SDK上限10MB |

KeyはFrontendへ送らず、`VITE_*` に置きません。起動はloopbackです。TabletへのLAN公開・HTTPS・顧客現場ネットワーク施工は未実施です。

## 自有資料と公開版

[資料説明](docs/DEMO_DOCUMENTS.md)、[公式出典一覧](research/SOURCE_MANIFEST.md)、[構造化調査値](research/public_data.json) を参照してください。

| 自有資料 | 内容 |
| --- | --- |
| [物件概要_demo.pdf](demo_documents/物件概要_demo.pdf) | No.15の価格・住所・面積・完成年月・間取り根拠 |
| [設備仕様_demo.pdf](demo_documents/設備仕様_demo.pdf) | No.15の設備15項目 |
| [周辺環境_demo.pdf](demo_documents/周辺環境_demo.pdf) | 駅・周辺施設の掲載範囲と限定 |
| [住宅ローン_demo.xlsx](demo_documents/住宅ローン_demo.xlsx) | MUFG・フラット35の参考金利・条件・日付・出典 |

基準日2026-10-07（Asia/Tokyo）。物件は登録2026-10-02・期限2026-10-15。金利は2026年10月借入／資金受取分・期限2026-10-31。実演前に公式情報を再確認してください。

No.15は土地建物税込76,900,000円、土地139.85㎡、建物93.25㎡。3LDKは公式図面からの分類。駅の最長徒歩12分・920〜950mは販売中4戸の掲載値で、No.15単独値ではありません。駐車可能台数は未確認です。

資料の版式と画面イメージは自作です。第三者の写真・図面・Bannerを転載しません。画面画像には「表示イメージ／実際の物件とは異なります。」と表示し、AIの事実根拠には使いません。

管理者は4資料をそれぞれ **アップロード → SDK解析 → raw・標準化結果と出典を照合 → 確認メモと確認チェック → 確認保存** します。必要な確認済み資料を全部選んで公開します。選択が新しい完全な公開版となり、前版へ自動追加する方式ではありません。

更新時は再アップロード・解析・確認し、更新元の旧資料を外して必要な設備・周辺・金利資料も選び、新版を公開します。新接客は新版、既存接客は開始時の版を維持します。異なる価格の旧・新概要を同時選択すると競合エラー。期限切れ・未来の資料は公開を拒否し、公開後の期限切れでも事実Toolを停止します。

FAQと金利Masterの編集は「確認データJSON」です。専用FAQ編集画面・任意資料の自動意味確定はありません。FAQは `question` / `answer`、金利は期間・参考年利・適用条件・出典を確認します。確認後の直接編集はできず、更新資料を新規登録します。元SDK rawと標準化結果は人の修正で書き換えません。詳細は [Demo操作手順](docs/DEMO_WALKTHROUGH.md)。

## 接客・住宅ローン・Staff

公開版アクセスは `get_property_overview`、`search_property_knowledge`、`get_mortgage_rates`、`calculate_mortgage`、`call_staff`。価格・金利はBackendの公開版から取得し、AIが任意の値を計算へ注入しません。

文字のローン対話は毎回、接客版の有効な金利Tool結果を取得して商品ID・日付を渡します。AI経由の計算は顧客の明示した商品選択をBackendで検証します。商品名・変動／固定等で選択が曖昧なら再確認し、AIの提案や「はい」だけでは新商品を承認しません。ローンフォームは表示された商品を選択して送信できます。

月額はDecimalの標準元利均等式、ボーナスなし・金利一定を仮定して1円単位へ丸めます。期限・商品年数・融資額を検証。フラット35は融資率9割以下の参考3.83%、9割超は公開済み代替3.94%です。実HTTPで76,900,000円・頭金5,000,000円・35年 → 借入71,900,000円・融資率約93.50%・参考3.94%・月額概算315,773円を検証しています。費用・税・保険・金利変化は含まず、審査可否は判定しません。

StaffボタンはBackendへ呼出記録を作り、認証した `/staff` が取得します。「受付」→ `accepted`、「対応完了」→ `completed`。CustomerもBackend状態を取得します。未完了の重複呼出を抑制します。審査断定依頼は方針説明とStaffへ進み、この方針文は生成AI回答と区別して表示します。

Voiceはユーザー操作後にマイクを要求し、SDPをBackendへ送信してWebRTCを接続します。Backend sidebandがTool・履歴を扱い、Frontendが音声・字幕・Avatarを扱います。文字入力は残ります。実完了にはChromeの日本語発話、AI音声応答、字幕、Tool、履歴の照合が必要です。

## 検証コマンド・証跡

```bash
backend/.venv/bin/python scripts/sdk_smoke.py
backend/.venv/bin/python -m pytest backend/tests -q
```

```bash
cd frontend
npm run build
```

| 証跡 | 対象 |
| --- | --- |
| [SDK Smoke](evidence/sdk/smoke_result.json) | 配布packageのPDF / Excel実読取、版・import元 |
| [HTTP acceptance](evidence/http_acceptance.json) | 独立test DBの取込・確認・公開、出典、計算、Staff受付・完了 |
| [Core review](docs/core_review.md) | 期限・不正型の修正とSDK入力回帰テスト |
| [実文字接客](evidence/live_text_acceptance.md) | 価格・設備・駅範囲・資料外質問・Staffと最初の対話所見 |
| [実AI版分離](evidence/live_version_acceptance.md) | 独立TEST PDF更新、SDK再解析、旧新版の実AI回答 |
| [ローン対話復験](evidence/live_loan_final.md) | 商品確認後の実Tool計算、条件提示の所見 |
| [実Chrome文字接客](evidence/live_browser/review.md) | 実AI回答・出典表示・版・保存履歴の画面検証 |
| [実Realtime](evidence/live_voice_review.md) | テスト音源による実挨拶・音声回答・字幕・Avatar・hangup 200。物理マイクは別確認 |
| [資料QA・ハッシュ](evidence/documents/artifacts.json) | 自有資料の描画・目視・SHA-256 |
| [最新acceptance](evidence/acceptance.md) | 全体テスト件数、Build・ブラウザー実測、BLOCKED / 未検証の正本 |

`scripts/http_acceptance.py` は `DEMO_MODE=test` の別インスタンス専用。通常DBを初期投入せず、利用者の管理者確認を代行しません。自動テストと人の実演受入れは区別します。

API形式は [API_CONTRACT.md](docs/API_CONTRACT.md)。公式参照は [OpenAI Responses](https://developers.openai.com/api/docs/guides/text)、[Realtime WebRTC](https://developers.openai.com/api/docs/guides/voice-webrtc?voice-api=realtime)、[Realtime server-side controls](https://developers.openai.com/api/docs/guides/voice-server-controls?voice-api=realtime)。文書確認と実API成功は別です。

## 現在の制限

- 少数のnative-text PDF / XLSX専用。OCR、旧XLS、複雑CAD・図面意味解析は未実装。
- 資料の対応関係はAdminが確認。自有資料キーとExcel明示ヘッダーを扱い、任意営業資料の業務意味を自動確定しません。
- 実AI文字回答とテスト音源による実Realtimeを検証済み。物理マイク・スピーカー、音声ローン対話の全工程、利用者の受入れは未検証です。
- 融資審査、法律・税務、投資価値保証はStaffへ引継ぎます。
- Responsiveを実装。物理Tablet・LAN・HTTPS・本番運用・負荷試験は未検証。
- SQLiteと単一BackendプロセスのDemo。本番認証やマルチプロセスのRealtime引継ぎは含みません。
