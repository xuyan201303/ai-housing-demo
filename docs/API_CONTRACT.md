# API contract — Customer R1 fields + R2 knowledge permission

2026-10-07。Base `/api`。字段表保留 [CUSTOMER_API_R1.md](CUSTOMER_API_R1.md)，新增许可与 AI 证据合同见 [CUSTOMER_KNOWLEDGE_R2.md](CUSTOMER_KNOWLEDGE_R2.md)。旧合同仅是历史记录。

Customer 接口除创建外必须携带 `X-Session-Token`；仅创建返回自己的 token，查询/轮询/选择/结束不重复返回。

| 路径 | 返回 |
|---|---|
| GET `/property` | 410 `PROPERTY_ENDPOINT_REMOVED`，不读取/返回最新发布版 |
| POST `/sessions` | CustomerSessionCreated；body `{mode: text或voice, property_id?: string或null}` |
| GET `/sessions/{id}` | CustomerSession |
| POST `/sessions/{id}/property` | CustomerSession；body `{property_id}`，有效/已发布/本接客版对象校验不变 |
| POST `/sessions/{id}/messages` | CustomerAnswer；body `{text}`，无原始 tool_results |
| POST `/sessions/{id}/mortgage` | CustomerMortgage；明确商品，selected 路径使用头金；未选对象使用申报借款额/年数/必要取得价格 |
| POST `/sessions/{id}/staff-calls` | CustomerStaffCall；body `{reason,last_customer_question?}` |
| POST `/sessions/{id}/end` | CustomerSession，status=ended，无 token |
| POST `/sessions/{id}/realtime` | 经认证的 `application/sdp` offer→answer，非JSON；本轮无真实服务调用 |
| POST `/sessions/{id}/realtime/greet` | `{status:greeting_requested}` |
| GET `/health` | 明确配置状态、SDK版、Demo模式、声线和非敏感指令指纹；无密钥 |

每份资料的 `document.scope=general/company/property`、人工确认、发布日期、不可变版本、Session 开始版固定、Tool 商品/金额验证不变。不存在有效发布版时可以 version=null 开始一般接客，不能获得未发布物件和金利。

Admin Basic `admin`；Staff Basic `staff` 或 `admin`，现有权限不降级。Admin 的 documents/detail/parse/confirm/publish/versions 与既有上传、SDK解析、人确认流程保留。`GET /admin/sessions` 使用独立 employee_view，保留快照和 Tool 参数等审计，递归移除凭据字段。Staff calls/accept/complete 保留业务理由、问题、Session ID、事务状态，并去除凭据字段。未知内部审计字段不作为 Customer 模型。

错误 `{error:{code,message}}`；验证错误固定为 INVALID_INPUT，无路径/原异常详情。请求体大小、上传限制和既有鉴权不变。默认 OpenAPI `/openapi.json` 是接口描述，未含业务记录；它不是生产部署安全已完成的证明。

R2：用途 customer/internal/unclassified 独立于 scope。确认 body 增加 usage（缺项未确认）；新增 `/admin/documents/{id}/usage` 的 `{usage,note}` 撤销旧确认，须实际重确认并新发布。旧快照不兼容放行。旧会话/许可变更返回 SESSION_RESTART_REQUIRED，仍可认证结束。health 增加非敏感 knowledge_boundary_version=2。

文字与 Realtime 应用出站共同使用源级权限和明确 AI evidence。固定指令不混文档正文，资料用数据/工具通道，错误不透传内部详情。TEST transport/socket 只验证应用边界，不验证真实 DataChannel 或模型抗注入。合法文本没有自动机密识别；混合资料整份排除，人工误标 customer 不会被白名单纠正。正常环境尚未统一切换。
# Phase 1 Japanese voice output additions

Existing R1/R2 contracts remain in effect. The new authenticated, event-bound speech endpoints and exact allowed fields are documented in [JAPANESE_VOICE_PHASE1.md](JAPANESE_VOICE_PHASE1.md#customer-api-additions). They accept no arbitrary synthesis text, snapshots or tool records. Old Realtime audio remains the default; Azure credentials and real listening are still pending.
