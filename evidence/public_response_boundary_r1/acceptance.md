# HOUSING_V1_PUBLIC_RESPONSE_BOUNDARY_R1 首轮验收

2026-10-07（Asia/Tokyo）。结果：HTTP Customer 字段边界及隔离前端流程 PASS；Realtime 仅服务端业务输出的脚本 socket 边界 PASS，上游实时通道整体 NOT_VERIFIED。不是完整 V1、安全部署或真实日语语音验收。

## CHANGED

- 新增 `backend/app/schemas/customer.py` 明确且嵌套封闭的返回模型；`customer_view.py` 逐字段构造，未知字段默认不返回。
- `/property` 关闭为410，不再读取发布版；Customer未依赖该入口。
- sessions start/view/property/end、messages、mortgage、staff-calls、realtime/greet 均使用顾客模型。创建自己的Session仍返回token；其余返回无token。完整snapshot/knowledge/FAQ/原tool_events/arguments/tool_results不下发。
- 产品列表只保留有效的安全选项与公开条件；资料联动变为明确的展示事件。当前展示只保留最近顾客发言之后的结果，历史消息另行保留且有历史标识，过期字段与缓存贷款卡不作当前条件。
- 来源只有通用展示label和经精确公共页面清单校验的url；不默认公开filename、手填location、raw scope_notes、服务器路径。应用层说明保留分譲全体距离不等于号地单独距离的必要限定。
- Admin使用独立employee_view，保留发布快照、工具参数和来源身份审计；Staff仍保留业务记录。员工payload递归移除凭据字段，而非全局裁剪审计。
- Realtime发送的function_call_output及Staff方针业务对象投影；未更换模型、声音、语音服务。
- Customer/Mortgage/CustomerSources读取新的明确类型和展示事件，不依赖内部工具记录。V1计划明确虚拟角色+日语语音接客为必要交付能力，文字仅开发验证/故障备用。

## VERIFIED

1. `backend_tests.log`：151 passed；1个既存Starlette/httpx弃用警告。相关Backend回归和8项R1测试包含实际HTTP路由调用（不是仅单测投影函数）。测试设置独立tmp DB，HTTP provider和socket均明示TEST，并禁止外部socket连接。
2. 顶层、物件、金利、knowledge、reference、Tool结果/参数、消息/会话、Staff记录的 internal_note/debug_payload/未知新增字段及 `TEST_INTERNAL_R1_DO_NOT_RETURN` 均未出现在已检查顾客响应。创建、轮询、选对象、消息、贷款、Staff、结束、greet逐个检查；未用全部空对象替代业务。来源文件名/位置与scope_notes的私有标记同样未返回。
3. 错token、另一Session token、无token均拒绝顾客读取/写入，包括Realtime入口；未发布对象选择拒绝；没有发布版的通用Session不读parsed/normalized；过期对象、候选、金利、搜索和当前试算不能经另一入口重取。已过期历史对话仍保留，并有历史标志。已有回归保留版固定价格7690/7700万的精确断言。
4. 未授权Admin/Staff访问拒绝；Staff不能访问Admin；授权Admin保留完整来源/参数审计。员工列表/动作不重复下发Session token。接受/完成仍走实际事务服务。
5. `chrome_result.json` + `customer-loan.png`：独立5184/8014实际HTTP+Google Chrome。明确TEST provider，不是实际AI/语音。一般首页→一般命中与安全来源→候选概要（无提前详情）→选择No.15→设备与必要距离限定→资料关闭并保持关闭→新查询自动展开→产品条件与实际Backend计算→Staff实际UI受付/完了与Customer轮询同步→结束。
6. Chrome已捕获实际Customer JSON响应，检查禁止字段/标记不可见，无页面JS错误。选中fixture房价7690万、头金500万、35年、1.195%月供209,563円；未选物件申报借入3000万的HTTP测试为87,439円。均为明确TEST数据，仅用于隔离验收。
7. Realtime脚本socket验证六类实际服务端业务输出保留物件价格、产品、月供与Staff pending，同时去除注入内部标记。没有连接真实Realtime、没有录音或物理麦克风测试。
8. `frontend_build.log`：TypeScript+Vite build PASS。`test_server_manifest.json`和`protected_scope_check.json`确认最终TEST服务源码与当前代码指纹相同。

旧测试预期的必要更新：`test_api.py`从snapshot.property改为property，数值/旧新版隔离仍精确断言；来源文档ID移至授权Admin审计断言，Customer断言安全标签且无filename/document_id；结束接口仅对客状态closed，挂断200仍对服务端持久状态断言。没有删除旧测试或降低上述业务验证。

首个Chrome脚本把同一来源在两个合法显示位置误判为只能有一个链接，已在 `chrome_first_harness_failure.json`保留失败；修正脚本计数，没有删除来源。最终记录为PASS。

## UNCHANGED / 隔离

- TEST专用DB：`evidence/public_response_boundary_r1/ui-test.db`；不是 `data/housing.db`，不是此前8001测试DB。没有复制DB，没有正常业务DB连接、确认、发布、清理或迁移操作。
- 正常DB文件大小/mtime与任务开始记录一致；仅核对文件元数据，不读取业务记录。`.env`、Backend requirements、Frontend lockfile指纹一致。
- SDK1.8.0既有安装与依赖、模型/默认音色、公开版本存储格式、确认发布、计算、Staff领域规则、Session鉴权保留；未访问SDK源码repo、未重装、未reset/clean、未提交。
- 付费AI调用0；无第三方服务、声音克隆、真人录音上传。Chrome无麦克风权限/采集。正常Backend未重启或切换。本次实际运行验收在隔离环境，正常5173不能据此标为最新合同已实测；其运行Backend需协调加载新合同后与新前端配套使用，未自动操作正常环境。

## LIMITATIONS

- 字段白名单不能识别answer/text/设备说明/条件等合法文本内夹带的内部机密。没有完成customer/internal资料分类，也没有完成顾客AI上下文保密隔离；不能导入真实混合公开/机密资料。
- 静态检查发现：Realtime初始及每轮instructions仍组装内部咨询上下文，模型可能收到较宽的公开资料结构。上游是否将Session配置/response指令、函数调用参数或其他事件原样送到浏览器，脚本socket不能证明；浏览器忽略未知事件不等于没有收到。服务端Tool输出已收窄，但以上独立provider通道仍有字段/上下文暴露风险，未实测或封闭，不能宣称所有传输渠道安全。
- 无员工独立账号、公开互联网部署安全、日语口音自然度或完整V1交付结论。文字TEST成功不能替代必要语音能力的真实验收。

## NEXT（仅建议，未执行）

下一最小任务：明确customer/internal资料用途并建立顾客AI可用上下文边界，同时逐项确认Realtime的Session/response/function事件是否含业务上下文及原参数。在获准的隔离条件下验证或收窄该独立传输路径，完成前不接入机密资料。正常服务的合同加载/兼容复验另行协调；本轮不自动部署或启动下一项。

完整出口与字段表：`docs/CUSTOMER_API_R1.md`；API合同：`docs/API_CONTRACT.md`。
