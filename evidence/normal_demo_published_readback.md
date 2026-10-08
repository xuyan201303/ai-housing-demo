# 正常Demo公開状態の読取 — 2026-10-07

読取時刻: 2026-10-07T01:46:20.122125+00:00

**WAITING_FOR_NORMAL_ADMIN_CONFIRMATION_AND_PUBLICATION**。ユーザーからの公開完了報告を正常8000の実状態でまだ確認できません。読取のみで、確認・公開・AI・接客Session作成を実行していません。

正常DB: `/Users/kyoen/Projects/ai-housing-demo/data/housing.db`。APIの文書ID／SHA-256と読取専用DBは一致。

資料 4件、SDK解析済み 4件、確認・公開済み 0件、公開版 0件、接客 0件。

`GET /api/property`: 409 / `NO_PUBLISHED_DATA`。5173のproxy healthはdemo、5174はtest。

| ファイル | 状態 | 正式ファイルSHA一致 | 確認日時 | 公開版 |
| --- | --- | --- | --- | --- |
| 住宅ローン_demo.xlsx | parsed | True | 未保存 | 未公開 |
| 周辺環境_demo.pdf | parsed | True | 未保存 | 未公開 |
| 設備仕様_demo.pdf | parsed | True | 未保存 | 未公開 |
| 物件概要_demo.pdf | parsed | True | 未保存 | 未公開 |

正常Adminで各資料の「管理者確認を保存」が成功し、4資料の公開対象チェックをすべて選び「選択資料を公開」を押した後、「現在の公開版」の版番号と成功通知を確認してください。確認・公開のエラーが表示された場合は、その表示内容を基に対応します。

この記録は先の [normal_demo_preparation.json](normal_demo_preparation.json) と [normal_demo_preparation.md](normal_demo_preparation.md) を変更しません。

実Chromeの正常Customer／Adminの読取画像は [normal_demo_published_chrome/result.json](normal_demo_published_chrome/result.json)。Customerは「資料公開待ち」で接客開始無効、Adminは4件登録／0件確認／未公開。画像を目視。JS page errorなし、mutationなし。公開資料のGETは実409のためconsoleにも2件409が残ります。これは未公開状態の実記録で、ゼロエラーとはしません。初回ハーネスのボタン名完全一致失敗も別保存し、実accessible labelへmatcherだけ修正しました。
