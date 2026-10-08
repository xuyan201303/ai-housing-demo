# 本輪の操作上の問題と最小修正

失敗画面・操作履歴を保持します。修正コードとブラウザー再確認は別です。下記は途中記録で、全体 PASS を表しません。

## 1. 未保存の編集がログアウトで失われる

- 発見方法：実 Chrome。保存していない FAQ 編集の状態で「ログアウト」を押すと、破棄の確認なしにログイン画面へ戻った。
- 初回失敗：[05-failure-unsaved-logout.png](05-failure-unsaved-logout.png) ／ [AX](05-failure-unsaved-logout.ax.txt)。
- 最小修正：Admin の既存 `unsaved` 状態を使い、ログアウト前に日本語の破棄確認を表示。キャンセルなら編集を保持する。
- 修正コード：`frontend/src/Admin.tsx`。Customer、Backend、確認・公開・用途・計算規則は変更しない。
- 実 Chrome 再確認：**PASS**。修正後に破棄確認を表示 [08](08-unsaved-logout-guard.png)。root が実 Chrome でキャンセル時の編集保持、明示破棄後のログアウト・再ログインを確認。本人の主観的な操作性受入れとは別。

## 2. 確認時の不足項目が現在の表示位置から見えない

- 発見方法：実 Chrome。不完全な FAQ を保存、再読み込み・再ログインで再開後、ページ下部の確認を実行。Backend は `質問を入力してください。` を FAQ の質問欄に返したが、視点は下部のままで不足箇所が見えなかった。
- 初回画面：[07-missing-question-error.png](07-missing-question-error.png) ／ [AX](07-missing-question-error.ax.txt)。不完全草稿と復元は [04](04-incomplete-faq-draft.png)、[06](06-incomplete-draft-restored.png)。
- 最小修正の範囲：最初の不足欄、または他の業務タブにある不足を示す摘要へ移動・フォーカスする。業務バリデーションや原資料は変えない。
- 実 Chrome 再確認：**PASS（不足箇所への移動・フォーカス）**。[09-missing-field-focused.png](09-missing-field-focused.png) と操作履歴に、同じ草稿の再確認失敗後の質問欄フォーカスが記録されています。欠落を補完後の確認成功は [10](10-faq-corrected-confirmed.png)。

## 3. 未公開の初回入口が既存版の更新と同じ説明

- 発見方法：実 Chrome。6 資料を内容・用途確認後、公開版が一つもない状態でも入口が「現在の公開版から草案を作成」と表示され、初回手順が分かりにくい。
- 初回画面：[12-first-publish-label-before-fix.png](12-first-publish-label-before-fix.png) ／ [AX](12-first-publish-label-before-fix.ax.txt)。
- 最小修正の範囲：公開版が存在しない場合だけ、「初めての公開草案を作成」と初回の説明を表示する。草案・確認・公開の Backend 規則は変えない。
- 実 Chrome 再確認：**PASS**。[13](13-first-publication-entry.png) で初回入口を表示、[14](14-first-publication-preview.png) で資料追加6件のプレビュー、[15](15-first-publication-success.png) でページから初めて v1 を公開。読み取り専用の [v1_readback.json](v1_readback.json) では、プレビューの全資料・確認・改訂と最終公開版が一致。
