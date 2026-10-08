# HOUSING_V1_ADMIN_FORMS — Phase 2 第1輪

判定：**PASS（本輪隔離技術驗收）**。這不是 Phase 1 真人語音體驗的接受記錄，也不是正常資料庫的發布。

- 隔離 Admin：<http://localhost:5175/admin>
- Backend：`127.0.0.1:8002`
- 專用 DB：`evidence/phase2_admin_forms/ui-test.db`
- [Chrome 截圖一覽](index.html) / [驗證結果](ui_results.json)
- 真正的 Google Chrome，專用 TEST profile；驗證後保持已登入 Admin 視窗開啟。

## 實際驗證

| 項目 | 結果與證據 |
|---|---|
| PDF / Excel 上傳及 SDK 解析 | 正式安裝的 SDK 1.8.0 實際解析六份資料，沒有 fake SDK。Chrome 業務流程中六次唯一解析；每份內容 SHA、SDK API、raw/normalized SHA 見 `sdk_parse_records.json`。Backend 回歸與單獨 SDK 檢查的調用不計入這個六次數字 |
| 物件表單 | 價格正確帶入；普通欄位編輯、存草稿、刷新並重新登入後由 Backend 恢復 |
| 設備 | 修改既有條目、增加 TEST 條目、刪除臨時條目 |
| FAQ | 依實際 SDK 原文手動整理問題及回答，修改、增加、刪除臨時條目，填寫資料位置與來源 URL |
| 住宅ローン | 商品顯示名與資料位置以 TEST 標記編輯；原金利、適用條件、期間、借入額及融資率條件全部保持來源原值 |
| 欄位錯誤 | 將既有商品有効期限暫時留空、保存不完整草稿；明示確認被拒絕，該日期欄旁顯示「金利の有効期限を入力してください。」；恢復原日期後明示確認成功 |
| 可選數值留空 | 以原資料實際存在的「融資率9割超の参考金利」驗證留空刪除 key；之後恢復來源原值，未發明金融条件 |
| 人工確認與發布 | 保存不會自動勾選確認；員工明示勾選並確認，之後另行選取四份對客 TEST 資料發布 v1 |
| R1 / R2 | 社內専用與未確認資料不能選作對客發布；後端拒絕社內専用發布；錯誤 Session token 與未授權 Admin 存取被拒絕 |
| SDK 資料不變 | 六份資料最終 raw、normalized SHA 均與解析時相同；手動編輯不冒充 SDK 讀取 |
| 已發布資料的草稿 | 在已發布物件保存新草稿；既有 reviewed、confirmation_id、公開版內容保持不變。新接客仍讀取原確認公開值，未讀取草稿 |
| 隱藏／未支援欄位 | 在隔離金利草稿加入未支援的巢狀 TEST 欄位，普通表單再次保存及確認後仍保留；該欄位沒有進入 Customer HTTP 回應 |
| 已有業務回歸 | 實際 Customer Chrome 物件選擇與設備卡、Backend 貸款試算、Staff pending→accepted→completed、接客終了均通過。Customer 回答為明確 TEST provider，不是實 AI／語音驗收 |
| PC 與 Responsive | 1440px Chrome 視圖與 1024px 無水平溢位，沒有 pageerror |

完整 Backend 回歸：**208 passed**，1 項既有 Starlette 警告。Frontend build：**PASS**。詳見 `backend_tests.txt`、`frontend_build.txt`。

## 保存的失敗歷史

1. `initial/chrome_result.json`：六份真實解析、五組編輯與草稿確認驗證通過後，TEST 改名僅套到一份物件資料，與設備資料名稱不一致。現有 `CONFLICTING_PROPERTY` 正確拒絕發布。只修正驗證資料的名稱一致性，未改業務規則。
2. `verified/chrome_result.json`：TEST 發布與可選數值檢查通過後，Playwright 對既有 Customer 下拉框使用過度嚴格的 label 選擇器，導致等待超時。只修正驗證腳本，未改 Customer 核心。
3. `accepted/chrome_result.json`：復用既有六份真實解析及 TEST 發布資料，完成後續 Customer、貸款、Staff、結束流程與最終畫面驗證。前述成功的操作區段保持其原始證據，沒有重新解析或新增付費呼叫。

## 未修改及限制

正常 `housing.db` 未進行資料庫連接、查詢或寫入；只以檔案 SHA-256 校驗未變更，沒有遷移、確認、發布或清理正常資料。`.env`、SDK、AI 模型、選定的 Nanami / chat / +15% / 1.15、Customer 核心、貸款與 Staff 規則均未更換。有料 AI／TTS 呼叫 **0**，未使用麥克風。

日常物件、設備、FAQ、基本金利與既有借入條件可透過普通表單操作。既有但未作成表單的特殊巢狀欄位（例如金利 `conditions` 陣列）保留原值；主動修改這些非日常項目仍需診斷用 JSON。SDK 原始結果與標準化結果可在折疊的診斷區閱覽，均不可由業務表單改写。

任意客戶 PDF 的自動整理、OCR、新版資料替換、發布差異比較、版本復元不屬於本輪。本輪測試的 TEST 編輯資料不能当作正常客戶資料發布。

下一輪：Phase 2 第二輪，資料替換、發布差異預覽、版本管理和恢復。**NOT_STARTED**。
