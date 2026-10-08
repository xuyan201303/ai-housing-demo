# Phase 2 第三轮：Admin 首次操作与日常更新验收

本轮从空 Admin 开始，由真实 Chrome 页面完成六份资料上传、正式 SDK 解析、普通表单核对、TEST 明确确认、首版 v1 发布及单份 FAQ 更新发布 v2。HTTP 仅用于读取操作结果，没有预先导入、确认或发布来补做页面步骤。

| 状态 | 结果 |
|---|---|
| ADMIN_FIRST_USE_FLOW | **PASS — TEST 浏览器流程**。初始0资料、0确认、0版本；页面完成首次导入至发布。 |
| ADMIN_UPDATE_FLOW | **PASS — TEST 浏览器流程**。FAQ 确认 #3 → #7，替换1、保留5、新增0、移除0；准备阶段保留 v1。 |
| CUSTOMER_DATA_INTEGRATION | **PASS — 实际资料 / Tools / Backend / Chrome 展示**。回答为 TEST provider，不是实际模型或语音验收。 |
| EMPLOYEE_USABILITY | 浏览器观察通过，三项实际操作阻塞已最小修复；**WAITING_FOR_USER_REVIEW**，未冒称真实员工已接受。 |
| NORMAL_ENVIRONMENT | **NOT_SWITCHED**。正常 DB 未 SQL 连接、迁移、确认或发布；后续操作须明确授权。 |
| PHASE2_TECHNICAL_STATUS | **PASS**，仅本轮隔离后台技术验收。用户主观受入、真实 AI / 语音、正常运营上线分别待验。 |

## 持久入口

- Admin：<http://localhost:5177/admin>
- Customer：<http://localhost:5177/>（使用「文字で開始」，本轮无麦克风）
- Staff：<http://localhost:5177/staff>
- Backend：`127.0.0.1:8004`；Frontend 代理实际指向8004。
- DB：`evidence/phase2_admin_e2e/ui-test.db`；Upload：`ui-uploads/`，不复制前两轮或正常库。
- 恢复命令：`zsh /Users/kyoen/Projects/ai-housing-demo/scripts/start_phase2_admin_e2e.sh`。已从 `/private/tmp` 实际执行成功，复用相同服务和持久库；不清空、不重新种数据。
- TEST 登录仅保存在本机 `TEST_LOGIN.txt`（0600），报告不输出凭据。[一页日文说明](../../docs/ADMIN_END_TO_END_GUIDE.md)。

页面和登录入口明确标注隔离数据、TEST provider。最终运行代码指纹与当前 Backend / Frontend 文件一致，见 [runtime.json](runtime.json)、[protected_check.json](protected_check.json)。

## 浏览器操作与只读核对

| 实际故事 | 页面证据 | 只读结果 |
|---|---|---|
| 首次登录，无资料／公开版 | [01](01-empty-first-use.png) | [初始空库](initial_empty_status.json)，8类业务表均0，无seed |
| 六份自有 Demo 资料各上传、SDK解析一次 | [02](02-property-candidate.png)、[03](03-equipment-confirmed.png)、[11](11-loan-conditions-form.png)及各文件 `.sdk-parsed.ax.txt` | [SDK及资料映射](sdk_parse_records.json)，SDK 1.8.0、原始文件SHA、raw/normalized哈希 |
| 普通表单整理设备、FAQ、金利conditions，不编辑JSON | [03](03-equipment-confirmed.png)、[10](10-faq-corrected-confirmed.png)、[11](11-loan-conditions-form.png) | 原有补足及数值条件保持；手填仅进入业务候选 |
| 不完整FAQ保存，刷新／再登录恢复，确认明确拒绝 | [04](04-incomplete-faq-draft.png)、[06](06-incomplete-draft-restored.png)、[07](07-missing-question-error.png)、[09](09-missing-field-focused.png) | 问题缺失显示「質問を入力してください。」；修正保存后页面确认成功 |
| 从零建立发布草案、添加6份确认资料、预览并明确发布v1 | [13](13-first-publication-entry.png)、[14](14-first-publication-preview.png)、[15](15-first-publication-success.png) | [v1读回](v1_readback.json)：全资料、确认ID、不可变改订ID与AX预览精确一致 |
| 日常更新：明确资料及理由、保存新FAQ、确认但不发布 | [20](20-update-entry.png)、[21](21-update-draft-saved.png)、[23](23-update-confirmed-not-published.png)、[24](24-new-v1-after-update-confirmation.png) | 确认后、发布前创建的一般接客仍由实际Tool取得A1；对应持久事件时间早于v2发布时间 |
| 查看差分、其他5份保持、明确发布v2 | [25](25-update-publication-preview.png)、[26](26-update-published-v2.png) | [v2读回](v2_readback.json)：只改1个确认；6个资料身份保持、v1整体快照哈希不变 |
| 旧接客v1重新读取A1，新接客v2读取A2 | [27](27-old-v1-after-v2-publication.png)、[28](28-new-v2-faq.png) | [三层联动证据](customer_data_integration.json)：发布内容、真实Tool事件、Customer AX文字分别保存 |
| 历史、未保存切换提醒和用户可再编辑表单 | [36](36-version-history-v1-v2.png)、[37](37-version-history-v2.png)、[38](38-unsaved-document-switch-warning.png)、[39](39-admin-ready-for-user-review.png) | v1/v2均保持；当前已登录FAQ页面保留供用户自评 |

六份资料：概要、设备、周边为 `property`；住宅购买基础FAQ、贷款基础FAQ及贷款Excel为 `general`。六份用途均由 TEST 浏览器明确确认 `customer`。一般FAQ PDF保留SDK原本文；SDK没有识别出结构化FAQ时，测试人员用普通表单手填一条明显标记TEST的FAQ（A1/A2），不冒充SDK识别事实。

原始 SDK raw / normalized 在首次发布前到 v2 后六份全体哈希一致。版本引用的确认关联不可变，旧FAQ确认#3仍属于v1，修订确认#7属于v2。[最终读回](final_readback.json)。

## Customer实际使用

一般首页和未选物件接客没有默认带入No.15；明确介绍与选择样本后才由 Tools 取得76,900,000円及15项设备。v2更新FAQ后这些资料仍可取得；卡片可展开／关闭。来源、金利条件与日期保持显示。

- v1：真实 Backend 计算，房价76,900,000円、头金5,000,000円、借入71,900,000円、35年、MUFG参考年率1.195%，月额 **209,563円**。
- v2未选房：人员通过普通计算表单明确输入借入30,000,000円、35年、同商品参考年率1.195%，真实 Backend 月额 **87,439円**；Tool 的物件价格和物件上下文为空，没有暗用样本价格。这不是 TEST provider 自动解析借款额的证明。
- 实际 `call_staff` → Staff页面「受付」→「対応完了」，Customer轮询同步 pending / accepted / completed，见 [30](30-staff-pending-customer.png)～[33](33-staff-completed-customer.png)。
- 3个Session均由Customer页面结束，最终只读状态全为 `ended`。这是文字接客结束验证，未声称麦克风或实际语音已关闭。

这些金额是隔离计算链路的结果，不证明实际融资适用条件或审查通过。实际模型事实引用、日语回答质量、声音、物理设备及抗幻觉不在本轮结论内。

## 发现、修复及保留限制

1. 未保存FAQ直接登出丢失：保留[05失败](05-failure-unsaved-logout.png)，补现有dirty状态提醒。实Chrome验证取消保持、明确放弃后登出／再登录。
2. 不足项在顶部、确认按钮在底部，失败后看不到错误：保留[07初次画面](07-missing-question-error.png)，首个错误字段／摘要自动定位，实Chrome [09](09-missing-field-focused.png)复验。
3. 无公开版时入口仍写当前版更新：保留[12](12-first-publish-label-before-fix.png)，只调整初次条件文案为「初めての公開草案を作成」，[13](13-first-publication-entry.png)复验。

具体记录见 [issues.md](issues.md)。另外保留非阻塞观察：25的FAQ前后表重复两行，值一致但略显冗余，未继续扩大修复范围。22的已选房会话被简化TEST provider路由到物件知识，未命中一般FAQ，**不作为A1通过证据**；改用真实未选房一般接客24／27／28证明资料链路，不把它说成真实模型路由成功。

14／25 PNG只记录当时视口的编辑区域和预览开头，**不声称截图包含完整差分表**；完整文字差分在同名AX及API读回。浏览器自动操作的确认与公开是TEST验收，不是用户本人批准。

`confirmed_update_before_v2_readback.json` 的只读取样晚于页面提交，实际捕获v2；文件明确保留这个时点偏差，不用于证明API在发布前仍只有v1。发布前使用23／24页面及时间早于v2发布的持久事件。

## 回归、保护与停止

Backend业务32文件哈希全部未改，直接引用前轮 [222 PASS日志](../phase2_document_update/backend_tests.log)，保留1个既有Starlette非推奨警告；不重复跑同套用例提高数量。恢复、并发、重复提交、用途撤回等沿用[前轮证据](../phase2_document_update/acceptance.md)，本轮没有改动其逻辑。最终 [Frontend build](frontend_build.log) PASS；上述3项UI变化已针对性实Chrome复验。

1056文件保护基线：正常DB本体/WAL/SHM、`.env`、依赖、原资料、SDK配布wheel不变，前两轮996份证据／库文件均不变。[保护记录](protected_check.json)。本轮仅4个Frontend文件变化（TEST标识及3项Admin阻塞修复）；Backend、SDK、语音、贷款、Staff业务规则未改。无paid AI/TTS、无SDK源码、无正常DB结构初始化。

当前环境保持可运行，用户任务仅：打开一份FAQ→修改一条→保存草稿→人工核对确认→查看发布差分→自愿明确发布→Customer文字新接客核对版本。**WAITING_FOR_USER_REVIEW**。

[正常升级说明](../../docs/DOCUMENT_UPDATE_NORMAL_UPGRADE.md)已更新但未执行；[当前代码真实AI证据缺口及另行授权的最小范围](real_ai_evidence_gap.md)单列。到此停止Phase 2第三轮，不开始Phase 3或第四轮后台开发。
