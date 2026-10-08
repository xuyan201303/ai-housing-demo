# Customer knowledge boundary R2

HOUSING_V1_CUSTOMER_KNOWLEDGE_BOUNDARY_R2 / 2026-10-07。
保留 [R1 Customer 字段合同](CUSTOMER_API_R1.md)。本轮是资料级用途与应用出站边界，不是自动机密识别或完整实时安全验收。

## 用途与确认

| 值 | Admin | 效果 |
|---|---|---|
| customer | 顧客への案内に使用可 | 实际确认内容和用途，再选入新发布版 |
| internal | 社内専用 | 保留员工原件与审计，不能对客发布 |
| unclassified | 未確認 | 新文件、旧记录缺项的默认，不能对客发布 |

用途独立于 `document.scope=general/company/property`。网站来源、解析成功、以前 confirmed/published 均不授予 customer 权限。一份混合文件整个排除，另提供经人工确认的对外版。

`POST /admin/documents/{id}/confirm` 增加 `usage`，省略为 unclassified。当前记录保存 `usage/confirmed_at/confirmed_by/confirmation_id`；不可变 confirmations 事件保存 reviewed、note、usage、actor、时间和 raw SHA。actor 来自实际 Basic 认证的共享 admin，不是个人账号。

新增 `POST /admin/documents/{id}/usage`，body `{usage,note}`。解析后可用；退回 parsed，清除当前 confirmation_id/confirmed_at，追加用途变更事件。即使选择相同用途也撤销旧确认。raw、normalized、历史确认、旧 versions 不改写。重新确认后须形成新发布版。

`POST /admin/publish` 只接受 customer 的有效当前确认。internal/unclassified 或缺确认依据报 `CUSTOMER_USAGE_REQUIRED`；未确认报 `UNCONFIRMED_DOCUMENT`。不能静默转用途。新快照仅增量增加 `document_approvals: {document_id: immutable_confirmation_id}`；原合并视图留作员工审计，无新表/迁移。

## 共用取资料规则

`knowledge_access.approvals/available_snapshot` 同时检查固定版本中的文档和确认 ID、不可变确认事件、当前用途和确认未被撤销、范围及日期。从批准事件的 reviewed 重建 property/knowledge/FAQ/rates/references，不使用已经合并的发布字段。旧快照没有审批指针，即使当前文件后来获批，也不会获得权限。

资料日期与商品日期都必须有效。物件各来源期限不能被其他文件续期；保留全部批准来源的限定。候选仅安全概要；详情、物件知识与物件范围商品需明确选择本版对象。共通商品支持未选房的申报借款额。贷款公式、产品条件校验、Staff 事务保持原实现。

共同入口：Session 创建/选择/轮询、Tools 的 context/一般/公司/物件检索/候选/详情/金利/计算、Customer 来源与展示、文字与 Realtime 出站。授权 employee_view 使用独立原快照，凭据过滤不变。R1 模型与展示事件不恢复完整快照出口。

## AI 证据合同

所有嵌套值来自封闭 `schemas/ai_evidence.py`；不发送完整业务 dict、SDK raw、备注、文件名、手填位置。

| 字段 | 内容 |
|---|---|
| version/property_selected/company_material_available | 必要状态 |
| customer_declared | 本人借款额/取得价格，明确不是企业资料事实 |
| property/property_scope_conditions | 已选有效对象的 R1 字段及全部批准来源限定 |
| properties | 主动要求候选时的安全概要 |
| items | 当前查询的完整依据、scope、受控 label/url |
| rates | 安全选项、完整 notes/conditions、期限/金额/年数、9割区分和输入条件 |
| mortgage | Backend 的 R1 结果；产品说明重新取自批准来源 |
| staff_call | 本 Session 三态和固定顾客提示 |
| error | 安全 code 与应用固定日文说明，不透传异常 |

欢迎不注入未请求的正文；每轮 context 按问题缩小依据。AI 不沿用 UI 600 字摘要。一次证据超过 18,000 个 JSON 字符时整体返回 EVIDENCE_BUDGET_EXCEEDED，要求缩小检索/Staff 确认，不截断尾部条件。

Responses：固定 instructions 只有应用规则。咨询/金利依据用 user 数据消息，工具结果用 function_call_output，不放 developer/system。每轮保留本人声明消息，旧 assistant 事实与缓存 Tool 结果不重放；每次请求前重验许可和本轮依据版本；Tool 循环中到期也停止并要求重开。

Realtime：保留 `/v1/realtime/calls` WebRTC + call_id sideband。Session/response instructions 只有应用规则。依据用 conversation.item.create 的 user/input_text；工具用 function_call_output；conversation.item.delete 替换上一份证据。Staff 与错误同样投影。许可或日期使已有缓存失效时不继续生成，要求结束并重开。

协议依据：[Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations)、[Realtime client events](https://developers.openai.com/api/reference/resources/realtime/client-events)、[Responses function calling](https://developers.openai.com/api/docs/guides/function-calling)，仅核对当前路线，日期 2026-10-07。TEST 捕获不是上游 DataChannel 分发或真实模型对抗验证。

## 历史和旧会话

新 Session 内部保存 knowledge_boundary=2 和批准来源指纹，不对客返回。旧会话缺标记或许可改变，Customer/AI 返回 409 SESSION_RESTART_REQUIRED，明确要求结束并新建。仍可认证结束，结束响应不带不安全历史；原件和旧版可供员工审计。

新会话旧回答作为 historical 显示，不作当前条件，不重发给文字模型。Realtime 日期变化拒绝复用已有 provider 缓存。已经向顾客公开的信息无法收回。

## 正常环境升级操作（本轮未执行）

1. 安排切换时间，让用户结束旧接客，不中断正在使用的会话。统一启动同版 Backend/Frontend，核对 health.knowledge_boundary_version=2；不能仅更新前端或恢复旧 snapshot 出口。
2. 正常 Admin 逐份查看已有文件，**不用重新上传**。旧文件缺用途均为未确认。已 confirmed/published 的资料：填写备注，点「用途を再確認（旧確認を無効化）」；照合全文、范围、来源、日期和用途，勾选后点「管理者確認を保存」。社内原件保留 internal。
3. 共通金利文件核对 general 范围和资料级日期；商品行保留自身日期及条件。内容正确不等于可对客使用；混合文件不标 customer。
4. 只选 customer 的必要资料，点「選択資料を公開」建立新版本，核对 document_ids、范围和版本；不修改旧快照。
5. 新接客核对使用新版本，旧会话按提示重开。真实麦克风、多轮语音和扬声器验收另行安排。

本轮未连接、迁移、确认或重新发布正常 DB，未重启正常 Backend。共享源码可能被既有 Vite 热更新读取；前端因此检查 R2 版本，未配套时阻止新接客及确认/发布，结束现有接客保留。正常 5173 不是本轮验收入口。

## 停止点

见 [隔离验收](../evidence/customer_knowledge_boundary_r2/acceptance.md)。独立 5186→8016，自有 TEST 资料与 TEST provider/socket，无付费 API/麦克风。内部正文标记、旧合并字段、缓存、许可/日期验证同时保留非空允许事实、贷款、来源及 Staff。

人工误标 customer、混合文件逐段权限、真实模型提示注入、上游实时事件、个人员工账号、公网安全及语音自然度均不在完成声明内。下一轮只建议员工资料表单、更新替换、发布差异预览，不自动开始。
