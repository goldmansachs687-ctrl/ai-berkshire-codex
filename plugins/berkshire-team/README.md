# AI 伯克希尔 · 完整投研团队 2.2.9

公开版插件 ID 为 `berkshire-team@berkshire-community`。基于 [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire) 的本地Codex适配，版权见LICENSE及THIRD_PARTY_NOTICES.md。

使用示例：

- “启动完整投研团队，研究腾讯。”
- “继续这个目录里的研究，先检查断点和缺失项。”
- “把我提供的《聪明的投资者》及笔记加入伯克希尔资料库。”
- “用伯克希尔复盘 AAPL 最新财报，区分公司实际结果与市场预期。”
- “查看 MSFT 的盈利预期变化，并说明哪些只是市场共识。”
- “先介绍 AAPL 的公司基本情况、基本财务、发展历史和重大历史事件。”

2.2.2新增[公司信息模块](skills/berkshire-team/references/company-info.md)：通过现有联网工具直接读取 Wiki 正文和公开券商/财经财务页面，或复用现有授权财务工具；无需额外 Wiki/券商插件。公司背景、基本财务、发展历史和重大事件放在正文第一节；只问本节不展开完整团队。网页不可读时更换来源，必要时用官方披露补证；不保证任意券商网站或 API 都可访问。此次是研究流程与模板更新，没有新增 MCP 服务、付费账户或财务 API 硬依赖。

2.0能力：四角色先独立判断、随后质询；最终独立复核；明确关键证据表；PASS/FAIL/INCOMPLETE三态核验；现金与资本配置估值约束；本地知识登记/字面检索/阅读范围与哈希；研究断点检查。原报告核验器的空值放行、单源差异放行和表格空格移列问题已修复。市值差异大于1%不再标已通过。

能力适配：Quartr及实际可用数据源；Public Equity Investing的标准化、DCF、可比估值、模型审计；Data的数据与结论检查；PDF/文档提取。只在发现可用且授权时调用，遵守目标技能的入口要求。不捆绑外部插件、不承诺市场覆盖、不自动购买/连接服务。适配规范不等于所有外部服务已完成联调。

需要Python 3.9+、联网及真实子代理能力运行完整团队。基础核验与资料脚本无第三方Python依赖；2.1的数据适配器使用单独安装的AKShare/EdgarTools环境。并发不够会分批；代理/额度不可用时如实报告未完成。研究保存工作区reports/berkshire-team，用户资料默认knowledge/berkshire。

资料工具只登记和检索UTF-8文本。PDF/EPUB/DOCX可先登记，正文提取需可用工具；未提取不宣称可检索。索引不等于读过，局部阅读不等于全书；未提供书籍留作待读。不会上传私人材料或自动训练模型。

验证：从插件根目录运行 `python3 -m unittest discover -s tests -v`。数值核验代码只检查提供的证据和定义，仍需读取原文及独立判断。PASS不是发布/买入批准；历史数字准确不保证预测正确。

安装与更新见[仓库说明](../../README.md)。源码改动应在插件源目录完成，再通过 Codex 重载。

2.2.1接入 Finance Skills 思路的美股财报复盘与盈利预期模块：同一入口按需调用，复用隔离数据环境，保存Yahoo原始数据包与错误；公司事实、市场预期和研究假设分开。未接入其 company-valuation 的固定参数或混合权重，现金估值仍沿用本插件规则。模块不自动调用付费服务、下单或开启监控。yfinance单独固定版本安装，见[模块说明](skills/berkshire-team/references/us-earnings.md)。新模块的短期数据不替代十年财务与长期商业研究；遵守工作区的报告结构与暂停要求。

2.1新增实际可执行的AKShare/EdgarTools只读适配器，支持港股/中国股票历史行情、港股财务原表、按截止日筛选的SEC申报、正文和XBRL三表。用market_data.py自检后调用，证据包保留原始行、来源、时间、截断及错误。详细入口见[本地数据说明](skills/berkshire-team/references/local-market-data.md)。数据环境要求Python 3.11+；基础研究脚本仍可用Python 3.9+。插件包不含虚拟环境、SEC联系身份或私人材料。

2.2将第一批书籍和伯克希尔公开资料的明确阅读片段转为8条带出处、适用条件和反例的规则，见[学习规则](skills/berkshire-team/references/learned-principles.md)。主动搜集或阅读后必须交付学习反馈，分别说明取得、阅读、规则应用和验证状态。部分问答仅核查搜索索引片段，正文403及缺失时间戳均注明。规则更新不代表模型权重训练或投资效果已证明；用户书籍全文、索引和私人配置不进入插件包。

## 2.2.3 长桥接入

新增已授权长桥工具路由、多期财务与行情结果规范化器，以及期间、空值、来源和错误边界测试。默认美股，Wiki背景历史和用户六部分顺序继续优先。规范化器不联网、无SDK/密钥依赖；连接器由用户已连接的Longbridge提供，不随插件复制。账户、持仓、预警和发布不属于默认公司研究。操作细节见 skills/berkshire-team/references/longbridge.md。

## 2.2.4 默认联合AIVA

完整公司研究默认以伯克希尔为唯一主流程，真实读取已安装启用AIVA的投资报告模块，分配分析标准给同一四角色并在复核前编辑。两者共用长桥等数据、证据、资料库、模型和用户六部分结构；十年财务与严格核验保留。记录joint-mode.json的加载及实际应用位置，未加载不称联合完成。详细见[联合模式](skills/berkshire-team/references/joint-mode.md)。

直接说“用伯克希尔＋AIVA联合模式研究XX”。显式“只用原伯克希尔”可关闭本次补强；只问公司信息或财报不启动完整团队。恢复旧研究不重跑或补造联合历史。AIVA仍独立安装，缺失时说明并沿用原流程，不自动安装。

## 2.2.5 估值工具链接

完整研究在估值阶段读取company-valuation适用方法，按需用现有FinanceToolkit隔离环境计算；复杂经营预测、Excel估值和工作簿检查交Public Equity Investing，真实并购/私有化等专项调用Investment Banking。主伯克希尔唯一调度，AIVA分析及表达保留，共用底稿/来源/模型。工具层实际执行记录为valuation-tools.json，不能以已安装/读取替代真实运行。详见[估值工具层](skills/berkshire-team/references/valuation-tools.md)。

方法权重、固定参数、现金/债务缺失补零和前瞻/历史倍数混用均不从上游示例直接导入。FinanceToolkit简化恒定增长DCF不替换复杂主模型，不自动装依赖或购买数据。公司信息/财报专项不扩大为全研究，旧研究不重跑。

## 2.2.6 报告与核验

统一六部分报告模板。独立双源核验会拒绝重复网址或相同的已记录原文指纹。独立复核完成需有非空报告和复核正文、实际复核者身份及绑定的证据记录。

## 2.2.9 多空辩论、进度面板与复核

在 Codex 中说「用 AI 伯克希尔完整研究 COST」即可启动。Leader 按可用席位调度四位研究角色、两位多空辩手和独立复核员，最后交付六部分报告及一页反馈。研究开始时会给出 `progress.html` 链接，在本地浏览器中可跟踪阶段、角色任务、底稿和改变研究方向的事件。[调度和恢复说明](skills/berkshire-team/references/team-progress.md)

多空双方各自提交开篇后互相质询。负责人用同一模型复算关键争议对现金流或每股价值的影响。独立复核完成后，交付检查区分完整交付、附限制可用和受阻。[辩论标准](skills/berkshire-team/references/debate-standard.md) · [交付验收](skills/berkshire-team/references/delivery-acceptance.md)
