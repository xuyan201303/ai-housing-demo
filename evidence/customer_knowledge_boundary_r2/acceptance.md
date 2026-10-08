# HOUSING_V1_CUSTOMER_KNOWLEDGE_BOUNDARY_R2

2026-10-07 / 最终状态：IMPLEMENTED_AND_VERIFIED_ISOLATED_APPLICATION_BOUNDARY。

## IMPLEMENTED

- 独立 customer/internal/unclassified 用途，默认/旧缺项为 unclassified；Admin 必须照合内容和用途。共享认证 admin、时间、备注、不可变确认 ID 记录在现有 JSON/confirmation 表中，无正常迁移。
- 用途变更撤销旧确认并追加历史；重新确认与新发布分开。旧 raw、确认、快照不改写。internal/unclassified 对客发布明确拒绝。
- 统一源级取资料，按固定版的不可变确认重建事实；不沿用被内部来源污染的合并 property/rates/FAQ。资料和商品各自期限、显式对象、范围、撤销批准同时约束。
- 保留 R1 Customer 模型/展示事件与来源；文字和 Realtime 共用封闭 AI evidence。完整正文/条件与 UI 摘要分开，超预算明确不足。保留全部来源限定，不透传 Tool 错误详情。
- 文档不放进高优先级指令；Responses user/Tool 数据，Realtime user/input_text/Tool 数据。历史 assistant/Tool 缓存不重发给文字模型；旧/撤销会话明确重开，Realtime 日期变化不复用缓存。
- 前端版本检查防止仅更新前端后继续确认/发布或新接客；正常切换说明见 [R2 合同及步骤](../../docs/CUSTOMER_KNOWLEDGE_R2.md)。

## VERIFIED

| 项目 | 结果与证据 |
|---|---|
| Backend 全部相关回归 | **165 passed**, 0 failed；[backend_final.txt](backend_final.txt) |
| Frontend TypeScript/build | PASS；[frontend_build.txt](frontend_build.txt) |
| 实际 Chrome | PASS，11 个流程检查；[chrome_result.json](chrome_result.json) |
| 文字每次实际应用出站请求 | TEST MockTransport；[text_outbound.json](text_outbound.json)、[错误分支](text_error_outbound.json) |
| Realtime 创建/欢迎载荷 | TEST HTTP + socket；[realtime_creation_outbound.json](realtime_creation_outbound.json) |
| 多轮刷新/查询/贷款/Staff/Tool 错误载荷 | TEST socket；[realtime_turns_outbound.json](realtime_turns_outbound.json) |
| 实例代码/代理/DB 配套 | 5186→8016，ui-verified.db，health boundary=2；[实例指纹](test_server_manifest.json)、[health](runtime_health.json) |
| 受保护配置/依赖及正常数据文件状态 | before/after 相同；[protected_before.json](protected_before.json)、[protected_after.json](protected_after.json) |

Chrome 使用明确的 TEST provider 和预置 TEST 解析状态，**不是实际 AI/语音或 SDK 新解析验收**。本轮 Backend 既有 SDK 回归继续通过已安装 1.8.0 原公开 API 离线读取自有 Demo PDF/XLSX。没有付费 API 或物理麦克风。

Chrome 实际操作：A-general/company/property/rates 对客确认；B-company internal、C-general unclassified 确认；分别选择 B/C 与 A 发布被拒绝；移出后只发布四份 A，新 Session v1。一般接客、候选、选中物件、资料展开/关闭、再次联动、Backend 月供 **209,563 円**、产品条件/来源、Staff pending→accepted→completed、结束同步都通过。另有未选房借款额 3,000 万円的 Backend **87,439 円** HTTP/文字/TEST Realtime 断言。所有数值仅 TEST 场景，不作为正常房源或实贷款条件证明。

隔离来源包含 A/B/C 三类同主题资料；B/C 的标记放在合法 knowledge、FAQ、价格 scope_notes、rates.notes 中。测试模拟历史合并字段污染、合法引用伪造缓存、旧 assistant/Tool 重放、文字 Tool 循环中到期时停止出站、未发布/未确认、expired/future、错误 token/另一 Session token、错误商品及对象、旧无用途快照、用途撤销/再次确认、新版固定与员工审计。允许 A 的事实、全文末尾否定条件、来源、计算结果确实到达模型请求，不能以清空资料通过。

恶意自有文档命令保留为 user 数据；请求社内来源仍受服务器许可限制，未改变 B 的 internal 用途或发布集合。没有真实模型抗注入测试。

测试合同变更：旧手写 fixture 显式加入 TEST 来源确认/审批指针和会话标记；金利共通来源显式 general 与资料日期。provider 金利依据从 developer 改为 user；Realtime 计算/Staff 断言读取新的明确 evidence 包装。保留既有金额、日期、版本、选择、Staff 等业务断言，不删除测试。首轮 3 个夹具失败及后续结果保留在日志中。

## NORMAL_ENVIRONMENT

未统一切换、未重启正常服务、未连接正常业务 DB，未确认或发布正常文件。末次检查未发现 5173/8000 监听，8000 health 不可达；只读取安全 health，没有业务数据查询。SDK、依赖、模型配置、.env 均未更换。未复制 TEST DB。

隔离 ui-test.db、ui-final.db 和各轮 Chrome/实例记录保留为 initial_* / before_turn_expiry_*；最终使用新的 ui-verified.db 再验收，最终装载源码指纹与工作区相同。这些 TEST 库均不用于客户演示。当前隔离入口仍运行：`http://localhost:5186/`、`/admin`、`/staff`。

后续正常升级须用户安排同版前后端切换、实际确认各已有资料用途、只发布 customer 新版、结束并重开旧接客。详见升级步骤；本轮未代行。

## LIMITATIONS

资料级分类依赖人工；误标 customer 的机密不能自动识别。混合文件整份不用于顾客，应提供独立对外版。上游真实 Realtime DataChannel 分发、模型抗提示注入、日语自然度、物理麦克风/扬声器及正常环境验收均 **NOT_VERIFIED**。员工仍是共享认证，不是个人账号；不代表公网安全或完整 V1 交付。

## NEXT

建议下一轮员工资料表单、更新替换、发布差异预览；尚未开始。本轮在资料用途与应用出站边界完成后停止。

机器记录见 [final_status.json](final_status.json)，交付文件哈希见 [artifact_hashes.json](artifact_hashes.json)。
