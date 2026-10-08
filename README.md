# 建売住宅販売向け AI接客Demo

> 2026-10-07 R2 更新：资料用途与应用 AI 出站边界已在隔离环境实施，正常环境尚未统一切换。当前合同/旧资料升级步骤见 [CUSTOMER_KNOWLEDGE_R2.md](docs/CUSTOMER_KNOWLEDGE_R2.md)，验收见 [R2 acceptance](evidence/customer_knowledge_boundary_r2/acceptance.md)。以下旧 Demo/实测记录均不代表 R2 已在正常 5173 验收。
建売住宅販売会社のAI接客員として、住宅購入・購入手続・住宅ローンの自由な相談を扱う独立ローカルDemoです。**資料取込 → SDK解析 → 管理者確認 → 範囲別公開 → 接客 → Backendローン概算 → Staff引継ぎ**。新規Sessionは物件未選択で、必要になった時にだけ資料を展開します。

物件サンプルは積水ハウス「コモンステージ八千代中央 分譲住宅 No.15」。一般相談には自動適用しません。公開事実をSANZOが自前の資料に再構成しています。SDK読取と管理者の業務確認は別の工程です。

正常Demoは従来4資料と共通FAQ2資料、計6件が実SDK解析済みで、人の確認・公開待ちです。会社のサービス・営業時間・保証の資料は未登録です。[接客定位・確認表・最短操作](docs/CONSULTATION_POSITIONING.md)。物理マイク・実スピーカーの受入れは正常5173で別途必要です。

**OpenAI API Key設定を反映し、実Responses文字回答とChrome WebRTC経由の実Realtime音声を検証しています。** 音声入力は明示した日本語テスト音源で、物理マイク・スピーカーの現場受入れは未検証です。SDK取込・確認・公開、Backend計算、Staff通知も実測済みです。最新定位の記録は [接客定位の検証](evidence/consultation_positioning/review.md)。[従来のacceptance記録](evidence/acceptance.md)は履歴を含み、旧定位の成功を新定位の受入れに転用しません。

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
| [住宅購入基礎FAQ_demo.pdf](demo_documents/住宅購入基礎FAQ_demo.pdf) | 物件を選ばない共通の購房基礎・出典・適用範囲 |
| [住宅ローン基礎FAQ_demo.pdf](demo_documents/住宅ローン基礎FAQ_demo.pdf) | Flat35の一般説明・手続・審査の非保証 |

基準日2026-10-07（Asia/Tokyo）。物件は登録2026-10-02・期限2026-10-15。金利は2026年10月借入／資金受取分・期限2026-10-31。実演前に公式情報を再確認してください。

No.15は土地建物税込76,900,000円、土地139.85㎡、建物93.25㎡。3LDKは公式図面からの分類。駅の最長徒歩12分・920〜950mは販売中4戸の掲載値で、No.15単独値ではありません。駐車可能台数は未確認です。

資料の版式と画面イメージは自作です。第三者の写真・図面・Bannerを転載しません。画面画像には「表示イメージ／実際の物件とは異なります。」と表示し、AIの事実根拠には使いません。

管理者は資料をそれぞれ **アップロード → SDK解析 → raw・標準化結果と出典を照合 → 下書き保存 → 確認メモと確認チェック → 確認保存** します。確認と公開は別の操作です。「公開内容を編集」は現在の公開集合を基に下書きを作り、追加・差し替え・除外を指定して差分を確認してから公開します。新しい公開集合は下書きに残した資料と確認改訂で構成されます。資料数やファイル名は固定しません。本輪は通常DBの取込・確認・公開状態を再確認していません。

更新は「新しいファイルに差し替える」と「登録内容を修正する」の二通りです。新ファイルはSDK解析と明示した差し替え元の関連を使い、内容修正は元のSDK証拠を使った独立改訂として保存します。準備・確認だけでは旧公開内容を取り下げず、他の合格な資料は次版にも保持します。新接客は新版、未撤回かつ有効な既存接客は開始時の版を維持します。用途の明示撤回と期限切れは即時制限されます。競合・未確認・社内専用・無効な日付はプレビューと最終公開で再検証します。

共通・会社・物件の範囲と出典・日付をAdminで確認できます。FAQと参考金利は普通の日本語フォームで編集し、金利の条件も行ごとに追加・修正・削除できます。未知の拡張項目は保持し、高度な診断区で確認します。任意資料の意味を自動確定する仕組みではありません。元SDK rawと標準化結果は人の修正で書き換えません。現在の更新手順は [資料更新・公開の社員向け説明](docs/DOCUMENT_UPDATE_PHASE2.md) を参照してください。

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
## 日本語音声出力（Phase 1）

新增可替换的语音输出：保留默认 OpenAI Realtime audio，另加 Realtime text → Azure 日语 TTS。当前缺 Azure 凭据，状态为 `READY_FOR_AZURE_CREDENTIALS`；本轮付费调用 0，自然度仍待用户试听。配置、事件绑定接口、试听工具和隔离验证见 [docs/JAPANESE_VOICE_PHASE1.md](docs/JAPANESE_VOICE_PHASE1.md)。不要以 TEST 电子音或浏览器播放成功替代真实日语试听及麦克风验收。

## Phase 2 第1輪：社員向け業務フォーム

Admin の物件・設備・FAQ・住宅ローン・資料本文/出典を通常の日本語フォームで編集できます。「下書きを保存」はBackendへ保存し、資料の用途・業務確認・公開とは分けて扱います。SDK raw/normalized と既存公開版は下書き保存では変わりません。確認済み内容を更新する際は、保存済み下書きを照合して明示的に再確認します。既存R2の承認更新ルールは維持されます。

第1輪の隔離入口は http://localhost:5175/admin（Backend 8002）です。`scripts/phase2_admin_test_server.py` は専用TEST DBと導入済みSDKを使用し、外部通信を禁止します。[第1輪フォーム説明](docs/ADMIN_FORMS_PHASE2.md) と [第1輪検証記録](evidence/phase2_admin_forms/acceptance.md) は当時の操作・証跡として保存します。現在の資料更新・公開操作は次の第2輪を参照してください。

## Phase 2 第2輪：資料更新・公開

隔離 Admin は http://localhost:5176/admin（Backend 8003）です。普通の更新では旧確認を保持したまま新改訂を準備し、現在の公開集合から保存可能な下書き・差分プレビュー・明示公開を行います。過去版の復元も現在の用途・期限を再検証し、新しい版を作ります。共有管理者の操作として記録し、二重送信や古いプレビューによる公開を防ぎます。

[社員の短い操作説明](docs/DOCUMENT_UPDATE_PHASE2.md)、[API契約](docs/DOCUMENT_UPDATE_API.md)、[隔離検証・Chrome証跡](evidence/phase2_document_update/acceptance.md)、[通常環境の後続更新手順（未実行）](docs/DOCUMENT_UPDATE_NORMAL_UPGRADE.md)。TEST回答は実AI・音声の受入れではありません。通常DB・SDK・`.env`・固定音声は変更せず、第3輪は開始していません。
