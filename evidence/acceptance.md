# 当前定位与状态：2026-10-07

Customer 已改为建売住宅販売会社のAI接客员，新Session物件未选择，资料按需展开/关闭，三类知识按确认发布控制。当前正常6件SDK解析済み・确认0・无公开版。公司资料MISSING。Backend138 tests/Frontend build PASS；新定位的实际文字、合成输入真实Realtime、Staff与媒体结束分项证据见 [当前定位验收](consultation_positioning/review.md)。正常人确认发布和物理麦克风/扬声器仍待完成，READY_FOR_CUSTOMER_DEMO=NO。

以下为此前收尾的历史记录。旧单物件定位、四资料数量及旧测试数量不能作为当前状态；失败证据保留。

# 実行検証記録

基準日: 2026-10-07（Asia/Tokyo）。OpenAI Key設定を反映してBackendを再起動し、実モデルの検証を追加しました。実接続、TEST、現場の受入れを分けて記録します。

## 正常Demoの今回の準備

- 正常5173が停止していたため既存のVite環境で再起動。正常8000はSDK 1.8.0・demo mode・AI設定あり。隔離5174/8001はtest modeで、proxyとDBを分離。
- 正常 `data/housing.db` に4正式資料を実アップロード→SDK解析。既存ハッシュ一致資料が無かったため各1件だけ登録。rawと標準化データを保存。管理者確認・公開は代行しない。詳細と人の確認表: `normal_demo_preparation.{json,md}`。
- 実Google Chrome headlessで正常Admin/Staffを読み取り検証、0 AI呼出・0確認/公開リクエスト、JSエラーなし。`normal_demo_chrome/result.json`。
- ユーザーの公開完了報告後に正常API・DBを再読取したが、2026-10-07 10:46 JST時点は4件parsed・確認0・公開版0。`normal_demo_published_readback.{json,md}`。申告だけで公開成功にはしない。
- その後ユーザーは「尚未实际操作，只是选了回复选项」と訂正。正常の業務確認・公開が未実施であることを確認した。準備済み4件から人の確認を待つ。
- `live_loan_final.md`の初回利率説明の旧所見を最新実装・後続 `live_rate_final` と照合。既に商品別条件を初回紹介へ適用する修正がある。再修正や新規文字AI呼出は不要。`current_rate_conditions_review.md`。
- 物理マイクはユーザーが「稍后进行真实麦克风验收」と回答。**WAITING_FOR_USER_MIC_TEST / READY_FOR_CUSTOMER_DEMO=NO**。正常4資料の業務確認・公開と正常5173の実機音声受入れが必要。

[最短の正常Admin・実マイク操作手順](../docs/NORMAL_DEMO_HANDOFF.md)。資料取込を再度ユーザーへ依頼しない。

## 実行済み

- SDK vendor ZIPのSHA256、ZIP内wheelと配布wheelの一致、独立Python 3.12.13 venv / SANZO SDK 1.8.0、実PDF / XLSX smoke: PASS。SDKソースrepo・代替パーサー不使用。
- Backend全テスト **119 passed**。最終結果は `final_status.json`。初回70 testsから、商品確認・金利文脈・終了競合の回帰を追加。
- Frontend TypeScript / Vite build PASS（36 modules）。実Google Chromeを使用。
- HTTP / Chromeの4資料取込→SDK解析→TEST確認→公開、Backend計算、Staff受付・完了、Customer同期: PASS。初期Key未設定記録は `http_acceptance.json` / `browser/` に保管。
- 実Responsesの価格・面積・設備・駅の4戸範囲・資料外質問・出典・保存: `live_text_acceptance.{json,md}`。
- 実Chrome文字接客1輪、実画面の参照表示、正確なSessionのSQLite読み返し: `live_browser/`。厳しすぎた文字一致判定とオフライン再評価の理由、初回結果を保存。追加AI呼出なしで再評価。
- 独立TEST PDFの実バイト更新→SDK再解析→確認→新版公開→実AI旧新版回答: `live_version_acceptance.{json,md}`。旧76,900,000円/v1、新合成TEST77,000,000円/v2が混在しない。
- 実ローン4輪: 商品選択前に計算せず、選択後にFlat35実Tool計算。借入71,900,000円・35年・9割超参考3.94%・315,773円/月。 `live_loan_final.{json,md}`。
- 商品条件の実1輪復験: Flat35の3.83%（9割以下）/3.94%（9割超）、MUFGの融資率条件未登録、各商品の金額・年数・2026-10-01～31: `live_rate_final.{json,md}`。
- 自有3 PDF / XLSX・独立TEST更新PDFは描画・目視確認。第三者の写真・図面不使用。

## シナリオ判定

| 場面 | 判定 | 範囲 |
|---|---|---|
| A SDK資料閉ループ | PASS（隔離実測） | 実SDK→TEST確認→公開→実AI回答と出典。通常DBの人の確認を代行しない。 |
| B 版更新 | PASS（独立TEST） | PDF実更新・SDK再解析・再公開後、実AIの価格・参照・履歴が版ごとに分離。新価格は合成値。 |
| C 住宅ローン | 対話計算・条件表示 PASS | 明示商品選択、実Tool計算、期限・商品条件・90%境界、参考条件の実説明。全ての言い回しの保証ではない。 |
| D 禁止判断 | Backend policy PASS | 審査断定を方針で拒否し実Staff recordを作成。モデル生成成功には数えない。 |
| E Staff | PASS | 独立Staff画面、受付・完了、Customer同期を実HTTP / Chromeで検証。 |
| F 音声 | 実API音声確認 / 物理マイク未検証 | Chromeへ日本語テスト音源を入力、実Realtime音声・駅範囲回答・字幕・Avatar・保存を確認。挨拶と終了の最新結果は `live_voice_review.md`。 |
| G 資料外 | PASS（代表質問） | 6kW EV充電器を資料なしに断定せず、確認できないとStaffへ案内。 |

## 実モデルで見つけた問題と修正

1. 商品選択前に2商品を計算: 初回 `live_text_acceptance` を保存。Backendで実顧客の明示選択を検証。文字・音声で共有し、曖昧な選択は再確認。明示送信するフォームは利用可能。
2. 次ターンで商品IDを失い、誤ID・期限を回答: `live_loan_revalidation` を保存。毎ローンターンに公開版金利ToolのID・ISO日付を渡す。選択後の復験は `live_loan_final`。
3. Flat35の9割条件をMUFGへ転用: `live_rate_presentation` を保存。Toolで商品単位の条件／未登録を明示し、元の公開版を変更しない。復験は `live_rate_final`。
4. 挨拶への割り込みで聴取Avatarがidleに戻る: 音声クリアでlistening / thinkingを消さず、実イベントで3状態を確認。
5. 終了時の古いSessionでRealtime終了状態を上書き: 最新レコードを取得する回帰を追加。媒体・Backendの終了順序を調整。上流hangupの実ステータスを記録し、未確認を200と扱わない。
6. 挨拶が追加のTool確認・物件説明へ進む: Backendで確認した物件名を渡し、初回応答だけToolを止めて短い実AI挨拶を生成する。

## TESTと実接続

`test_ai.py` / `test_realtime.py` の応答は明示したTEST scripted fixturesで、実外部API成功には数えません。実接続記録は `live_*`。初期503、誤回答、ハーネス早期終了・照合失敗は保管し、後の成功で削除していません。

音声入力はmacOS Kyokoの合成テスト音源、出力は実OpenAI Realtime生成音声です。物理マイクの受入れには代用しません。モデル変更・mock成功fallbackはありません。各修正後の新しい検証を別Session・別ファイルに保存しています。

## 実演時に残る確認

通常 `data/housing.db` は4資料がSDK解析済み。最後のAPI読取では確認0件・公開版0件で、管理者がRaw・出典を照合して確認・公開する段階です。前回の資料0件状態は旧 `final_status_before_normal_preparation.json` に保存。自動確認・自動公開は行っていません。

通常は :5173 / :8000。隔離 :5174 / :8001 は診断用に起動しています。正常資料を公開してから正常5173で物件・設備・連続ローン・Staff・終了を実マイクとスピーカーで確認してください。ユーザーは実マイク確認を後で行うと回答し、成功の回答は未受領です。

物理マイク・スピーカー、音声ローン対話の全工程、物理Tablet、LAN、HTTPS、本番・負荷試験は未検証です。

## 既知の範囲

native-text PDF / XLSXの少数自有資料が対象。OCR、任意営業資料の自動業務正解推定、CRM、融資審査・税務判断は対象外。No.15単独の正確な駅分数・駐車台数は未確認です。物件期限2026-10-15、金利期間2026-10-01～31以降は再確認が必要です。単一FastAPIプロセス。テスト時にStarletteのhttpx DeprecationWarningが1件あります。
