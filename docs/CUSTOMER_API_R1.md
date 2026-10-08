# Customer API R1 — 明确字段表与全部出口

任务 HOUSING_V1_PUBLIC_RESPONSE_BOUNDARY_R1 / 2026-10-07。

只允许下列字段，所有嵌套对象也使用明确模型，无 dict/Any 透传。模型 extra=forbid；应用投影逐字段构建，不把原始字典交给响应模型裁剪。字段未进入表时，默认不返回。

## 出口审计

| 出口 | 原返回 | 现返回与限制 |
|---|---|---|
| GET /property | 最新完整快照 | 410，前端不依赖此接口，不再读取发布版 |
| session start | record + 完整/部分快照 | CustomerSessionCreated，自有token仅此次返回，未选对象property=null |
| session view/polling | record/snapshot/messages/tool_events/staff_calls | CustomerSession，无token，无快照或原始工具 |
| property selection | shared view | CustomerSession，仅明确且有效的对象详情 |
| message | AiService原始返回 | CustomerAnswer，answer/安全来源/展示事件/自有Staff状态 |
| mortgage | 原Tool计算返回 | CustomerMortgage，Backend实算、版本/条件/期限保留 |
| staff-call | 原Staff业务对象 | CustomerStaffCall，三态与顾客可见提示，不下发内部理由/员工备注 |
| session end | shared view | CustomerSession，ended，不返回token或挂断调试 |
| realtime/greet JSON | 服务结果 | CustomerGreeting明列status |
| realtime SDP | provider SDP | 非JSON，维持认证和格式检查；本轮无真实API验证 |
| GET /health | 明列配置状态 | 固定字典字段，无认证值，非业务数据库出口 |
| GET /openapi.json | API模型描述 | 没有业务对象，不是公网部署验收 |
| provider DataChannel/sideband | 原Tool结果可经provider回传 | 发送的业务结果投影；上游参数/Session事件/音频通道整体尚未实测隔离 |

## 范围、来源、历史

- property_id=null 仍可开始一般咨询。候选仅 property_id/property_name，不提前给价格、地址、面积、设备。显式选择使用本Session固定发布版与已有 validate_property。
- 产品选项由固定版有效 rates 逐字段投影，保留商品、9割金利区分、期限、金额/年数界限、条件和来源；不是完整金利对象。无需选物件也能选择商品和申报借款额，计算仍由既有Backend执行。
- display_events 只保留本次最近顾客发言之后仍有效的显示结果（不重发此前查询的完整展示历史），把内部 Tool 事件映射为 properties/property/sources/products/mortgage 五类。只保留安全显示结构和事件序号，无 Tool名称或 arguments。get_consultation_context 不是资料展示事件；完整 knowledge/FAQ 不下发。搜索片段最多8条、每条600字正文窗口（可附省略号），保留命中查询附近内容。
- 来源统一 label/url。没有公开名称依据时用确认・公開済み物件資料/住宅購入資料/会社資料/参考金利資料。document_id、filename、管理员 location、source_name 等不对客；不使用模型判断保密性。
- URL必须精确匹配应用 `PUBLIC_SOURCE_URLS` 已核对公共页面，同时是https、无账号密码/端口/查询/fragment。未经列入的页面、其他路径、协议、私网URL均不给链接，仅保留标签。图纸图片、文件路径不自动放行。新客户公共链接需显式审核后加入清单，本轮未增加后台设置。
- scope_notes原文字不默认公开；使用应用明确业务提示保留“分譲全体范围不可当成号地单独距离”的限定，不能把备注当成精确距离依据。
- 每次poll重新检查日期。过期物件、候选、产品、命中与当前试算展示被撤下；消息保留历史并标为historical=true，UI说明会话是当时的案内。缓存贷款卡在产品失效或物件依据撤下时清除，不能当当前条件继续使用。
- Admin/Staff独立授权视图保留审计，递归删除token/session_token/api_key/password/authorization字段。Customer会话token不在轮询、结束或员工日志中重复下发。合法文本中嵌入秘密不由字段白名单识别；不得导入混合机密资料。

## 字段模型

以下字段来自 backend/app/schemas/customer.py，前端对应 customerTypes.ts。可选/空值不代表允许其他字段；列表元素均有明确模型或仅字符串。

### CustomerSource

| 字段 | 明确类型 |
|---|---|
| `label` | `<class 'str'>` |
| `url` | `str \| None` |

### CustomerProperty

| 字段 | 明确类型 |
|---|---|
| `property_id` | `<class 'str'>` |
| `property_name` | `<class 'str'>` |
| `lot` | `str \| None` |
| `price` | `float \| None` |
| `address` | `str \| None` |
| `layout` | `str \| None` |
| `station` | `str \| None` |
| `walking_minutes` | `float \| None` |
| `land_area` | `float \| None` |
| `building_area` | `float \| None` |
| `completion_date` | `str \| None` |
| `parking` | `str \| None` |
| `equipment` | `list[str]` |
| `surroundings` | `list[str]` |
| `scope_notices` | `list[str]` |
| `checked_at` | `str \| None` |
| `effective_date` | `str \| None` |
| `valid_until` | `str \| None` |
| `references` | `list[CustomerSource]` |

### CustomerCandidate

| 字段 | 明确类型 |
|---|---|
| `property_id` | `<class 'str'>` |
| `property_name` | `<class 'str'>` |

### CustomerProduct

| 字段 | 明确类型 |
|---|---|
| `id` | `<class 'str'>` |
| `bank` | `<class 'str'>` |
| `product` | `<class 'str'>` |
| `rate_type` | `<class 'str'>` |
| `rate` | `<class 'float'>` |
| `rate_over_90_percent` | `float \| None` |
| `effective_date` | `<class 'str'>` |
| `valid_until` | `<class 'str'>` |
| `years_min` | `int \| None` |
| `years_max` | `int \| None` |
| `loan_amount_min` | `float \| None` |
| `loan_amount_max` | `float \| None` |
| `max_loan_to_value` | `float \| None` |
| `notes` | `<class 'str'>` |
| `conditions` | `list[str]` |
| `requires_acquisition_price_for_estimate` | `<class 'bool'>` |
| `references` | `list[CustomerSource]` |

### CustomerMortgage

| 字段 | 明确类型 |
|---|---|
| `version` | `<class 'int'>` |
| `rate_id` | `<class 'str'>` |
| `bank` | `str \| None` |
| `product` | `str \| None` |
| `rate_type` | `str \| None` |
| `property_price` | `float \| None` |
| `down_payment` | `float \| None` |
| `loan_amount` | `<class 'float'>` |
| `annual_interest_rate` | `<class 'float'>` |
| `years` | `<class 'int'>` |
| `monthly_payment` | `<class 'int'>` |
| `calculation_date` | `<class 'str'>` |
| `effective_date` | `<class 'str'>` |
| `valid_until` | `<class 'str'>` |
| `rate_basis` | `str \| None` |
| `price_basis` | `str \| None` |
| `loan_to_value` | `float \| None` |
| `loan_to_value_percent` | `float \| None` |
| `conditions` | `list[str]` |
| `product_notes` | `<class 'str'>` |
| `notes` | `<class 'str'>` |
| `references` | `list[CustomerSource]` |

### CustomerHit

| 字段 | 明确类型 |
|---|---|
| `text` | `<class 'str'>` |
| `scope` | `Literal['general', 'company', 'property']` |
| `references` | `list[CustomerSource]` |

### PropertyDisplay

| 字段 | 明确类型 |
|---|---|
| `event_id` | `<class 'int'>` |
| `kind` | `Literal['property']` |
| `property` | `<class 'CustomerProperty'>` |

### CandidatesDisplay

| 字段 | 明确类型 |
|---|---|
| `event_id` | `<class 'int'>` |
| `kind` | `Literal['properties']` |
| `properties` | `list[CustomerCandidate]` |

### SourcesDisplay

| 字段 | 明确类型 |
|---|---|
| `event_id` | `<class 'int'>` |
| `kind` | `Literal['sources']` |
| `items` | `list[CustomerHit]` |

### ProductsDisplay

| 字段 | 明确类型 |
|---|---|
| `event_id` | `<class 'int'>` |
| `kind` | `Literal['products']` |
| `products` | `list[CustomerProduct]` |

### MortgageDisplay

| 字段 | 明确类型 |
|---|---|
| `event_id` | `<class 'int'>` |
| `kind` | `Literal['mortgage']` |
| `result` | `<class 'CustomerMortgage'>` |

### CustomerMessage

| 字段 | 明确类型 |
|---|---|
| `event_id` | `<class 'int'>` |
| `role` | `Literal['user', 'assistant']` |
| `text` | `<class 'str'>` |
| `created_at` | `str \| None` |
| `channel` | `Optional[Literal['text', 'voice', 'policy']]` |
| `references` | `list[CustomerSource]` |
| `historical` | `<class 'bool'>` |

### CustomerStaffCall

| 字段 | 明确类型 |
|---|---|
| `id` | `<class 'str'>` |
| `status` | `Literal['pending', 'accepted', 'completed']` |
| `customer_message` | `<class 'str'>` |
| `created_at` | `str \| None` |
| `accepted_at` | `str \| None` |
| `completed_at` | `str \| None` |

### CustomerVoiceError

| 字段 | 明确类型 |
|---|---|
| `code` | `Literal['VOICE_CONNECTION_ERROR']` |
| `message` | `<class 'str'>` |

### CustomerRealtime

| 字段 | 明确类型 |
|---|---|
| `status` | `Literal['not_started', 'connecting', 'connected', 'closing', 'closed', 'error', 'disconnected']` |
| `error` | `CustomerVoiceError \| None` |

### CustomerSession

| 字段 | 明确类型 |
|---|---|
| `id` | `<class 'str'>` |
| `version` | `int \| None` |
| `mode` | `Literal['text', 'voice']` |
| `property_id` | `str \| None` |
| `status` | `Literal['active', 'ended']` |
| `created_at` | `<class 'str'>` |
| `ended_at` | `str \| None` |
| `property` | `CustomerProperty \| None` |
| `products` | `list[CustomerProduct]` |
| `messages` | `list[CustomerMessage]` |
| `display_events` | `list[Annotated[PropertyDisplay \| CandidatesDisplay \| SourcesDisplay \| ProductsDisplay \| MortgageDisplay, FieldInfo(annotation=NoneType, required=True, discriminator='kind')]]` |
| `staff_calls` | `list[CustomerStaffCall]` |
| `realtime` | `<class 'CustomerRealtime'>` |

### CustomerSessionCreated

| 字段 | 明确类型 |
|---|---|
| `id` | `<class 'str'>` |
| `version` | `int \| None` |
| `mode` | `Literal['text', 'voice']` |
| `property_id` | `str \| None` |
| `status` | `Literal['active', 'ended']` |
| `created_at` | `<class 'str'>` |
| `ended_at` | `str \| None` |
| `property` | `CustomerProperty \| None` |
| `products` | `list[CustomerProduct]` |
| `messages` | `list[CustomerMessage]` |
| `display_events` | `list[Annotated[PropertyDisplay \| CandidatesDisplay \| SourcesDisplay \| ProductsDisplay \| MortgageDisplay, FieldInfo(annotation=NoneType, required=True, discriminator='kind')]]` |
| `staff_calls` | `list[CustomerStaffCall]` |
| `realtime` | `<class 'CustomerRealtime'>` |
| `token` | `<class 'str'>` |

### CustomerAnswer

| 字段 | 明确类型 |
|---|---|
| `answer` | `<class 'str'>` |
| `version` | `int \| None` |
| `references` | `list[CustomerSource]` |
| `display_events` | `list[Annotated[PropertyDisplay \| CandidatesDisplay \| SourcesDisplay \| ProductsDisplay \| MortgageDisplay, FieldInfo(annotation=NoneType, required=True, discriminator='kind')]]` |
| `staff_call` | `CustomerStaffCall \| None` |

### CustomerGreeting

| 字段 | 明确类型 |
|---|---|
| `status` | `Literal['greeting_requested']` |

