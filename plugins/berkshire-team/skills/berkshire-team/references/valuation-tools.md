# 估值工具层：统一调度与实际调用

用户已要求把新装FinanceToolkit、company-valuation链接进伯克希尔，并同意此前讨论的Public Equity Investing / Investment Banking按需支援。它们是本任务中的方法、计算或建模能力，不是新增事实来源，也不启动额外完整研究团队。本页适用于联合和原伯克希尔独立模式；用户明确限制工具时服从。

## 何时选什么

| 需要完成的工作 | 默认路由 | 与主流程衔接 |
| --- | --- | --- |
| 进入完整公司研究的估值阶段 | 实际读取company-valuation及相关方法参考，再按下列覆盖规则使用 | 财务角色选适用方法，保存方法选择及拒绝理由；不重复全公司取证 |
| 财务比率或简单DCF/DDM的计算复算 | 现有独立环境中的FinanceToolkit | 显式传入已核口径和参数，保存输入、版本、结果；不是数据源或完整估值替代品 |
| 需要可修改Excel模型、复杂经营预测或主模型尚不足以表达经济驱动 | Public Equity Investing：financials-normalizer（有口径混乱时）→ three-statement-model-builder（确需三表预测时）→ dcf-model-builder / comps-valuation | 只调用缺少的步骤，使用同一证据包与预测；DCF和可比各做适用检验，不按表格机械全跑 |
| 新生成或实质修改了Excel模型，或存在公式/来源疑点 | Public Equity Investing的model-audit-tieout | 在最终独立复核前检查工作簿，不能替代主插件证据门禁或声称独立代理复核已完成 |
| 明确并购、私有化、收购融资或交易拆分场景 | Investment Banking：按任务选择comps-valuation、merger-model-builder或lbo-model-build | 公共交易倍数、控制权溢价、协同及融资假设分开，写交易专项附录；普通上市股权估值仍由Public Equity路径承担 |

SOTP本身不自动触发投行流程；没有并购/交易背景的多业务公司仍由财务角色用公司披露分部和适当同行估值。禁止因两个插件都有DCF就各建一份并平均；若确需第二实现复算，输入假设须相同，差异逐项解释。

## 定位能力、解释器与记录

1. company-valuation以本轮技能目录提供的真实SKILL.md路径为准，完整读取，再按方法读取references/dcf.md、relative_valuation.md、sotp.md或wacc_erp_rates.md。找不到技能则记录不可用，继续主插件估值，不按名称猜路径或自动重装。
2. 本项目已安装FinanceToolkit的环境为实际工作区下 `.runtime/valuation-tools/bin/python`。先解析工作区绝对路径，使用该解释器执行company-valuation里的Python步骤；不改系统Python、不改market-data环境，也不自动执行原技能的pip安装。换工作区时先核现有配置，不能假定该相对环境必然存在。
3. 检查版本与依赖可用性：用上述解释器执行 `from importlib.metadata import version; from financetoolkit.models import intrinsic_model; import numpy, pandas, yfinance; print(version("financetoolkit"))`。缺失如实降级，不在主代理全局环境补装，不把导入通过称在线行情可用。
4. 两个专业插件从当前会话提供的路由SKILL.md真实路径定位；读取其入口和调用政策，再按精确路径读所属插件的目标技能。两个插件同名的dcf-model-builder等必须带插件身份，不能误用全局或另一插件的同名文件。宿主未提供时用受支持插件查询/发现；只有缓存目录或名称不能证明当前可调用，无法确认时仅记录可读，不称已启用。插件不可用则保留已有主模型及明确缺口，不自动安装或虚构工具。
5. 每次真实估值在研究目录新增 `valuation-tools.json`，记录工具/插件版本、实际模块/脚本路径与SHA256、解释器、选择原因、输入/来源ID/期间/币种/单位、执行命令、返回码、输出路径、限制。区分available、loaded、executed、failed、skipped；读指令不算执行模型，安装验收不算公司研究。可以引用joint-mode.json，不能给旧研究补造调用记录。

## FinanceToolkit计算边界与直接入口

目前安装2.3.1。优先使用只计算、不抓取数据的底层函数：

```python
from financetoolkit.models.intrinsic_model import (
    get_free_cash_flow_to_firm,
    get_intrinsic_value,
    get_gorden_growth_model,
)
```

- `get_free_cash_flow_to_firm(nopat, da, capex, delta_nwc)`：资本开支用正的支出额，营运资本增加为正占用，释放为负。先按来源定义做符号桥，不对delta_nwc取绝对值。该公式不能替代SBC、租赁、少数股东和利润到现金的经济调整。
- `get_intrinsic_value(...)`：只适合恒定增长、年末现金流折现的简化FCFF复算；必须显式传cash_flow、growth_rate、perpetual_growth_rate、weighted_average_cost_of_capital、cash_and_cash_equivalents、total_debt、shares_outstanding、periods和short_term_investments，并核定wacc>g、股数>0、期数为正整数、数值有限。金额/股数采用一致单位。非经营资产只有在现金流中已剥离其收益后才加回。
- 分阶段增长、逐年资本强度、SBC/租赁或复杂资本桥不能用该简化函数替换主模型。需要主模型之外的资本桥时单独列明，短期投资、现金、优先股、少数股东不遗漏或双算。FCFE不传入FCFF/WACC接口。
- DDM仅在分红能力和资本要求适合时使用；折现率为股权成本，参数须有依据。其他库函数也须先核当前签名和经济假设，不能因库提供方法就自动套用。
- 用Decimal或独立实现检查关键每股结果；FinanceToolkit的浮点输出不是精确十进制，也不算财务事实的独立第二来源。无明确分布依据不自动运行蒙特卡洛或给情景编概率。

## company-valuation原文的必要覆盖

保留上游技能文件，仅在本主流程映射其方法。以下明确优先于原文默认示例：

- 不使用50/50、40/30/30机械混合；多方法解释适用性、差异和取舍。Gordon终值与退出倍数也不默认取中点或统一15倍。
- 不自动接受4.5%无风险利率、5.5%ERP/债务成本、2.5%永续增长、五年预测、行业beta或三年中位利润率；逐项记录有日期的来源或研究理由，固定数只能作为已披露的条件假设。历史财务仍优先十年，预测期另选，不与历史覆盖混淆。
- 现金、债务、beta等缺失不以 `or 0` / `or 1`补齐；零与未知分开。分部缺失不编SOTP，未盈利企业不能用不存在的收入倍数造值。
- 现金流中的营运资本变动保留经济方向；前瞻PE配同期间预测EPS，TTM PE配TTM EPS，不能用前瞻同行倍数乘历史EPS并冒称同口径。
- SBC逐公司评估经济成本，不能只因是工业/消费企业便忽略。公司事实、公司指引、分析师共识与本模型预测分开，不用外部目标价倒推想要的模型结果。
- WACC不大于终值增长率时停止该估值或重建有依据的假设，不为得到输出机械压低g。银行保险、REITs及周期企业按适用方法处理。

## 专业插件的受控交接

财务角色输出共用模型输入及来源ID，明确证券/截止日、金额和股数单位、年度/TTM/预测期间、FCFF/FCFE及资本桥、SBC/租赁处理、情景与参数依据。专业模块产生的plan/workbook只是这一模型的实现或分方法组件；有假设差异必须写清并回到责任底稿确认，不能悄悄替换。

- Public Equity的公式工作簿按其真实技能的validate_plan.py、build_banker_formula_workbook.py等入口执行；具体参数以已读版本为准。只有builder成功、必需表/公式及model_citations.json存在且运行记录确认时才能称公式工作簿。示例模板一律标模拟，不残留为真实公司数据。
- 当前Public Equity 0.1.31模板为六列预测，而示例plan为五年，builder会延长/截断并复制末期参数；真实研究必须先对齐预测期及每年假设，逐项检查运行警告，不能把自动补齐的年度或来源缺失时的0.0价格当已研究数据。缺价格不计算涨跌空间，NWC仅映射到应收代理时明确局限。
- 构建器不保证计算Excel公式，文件存在、公式数或缓存值不代表重新计算。查看运行记录及工作簿，必要时用已可用的表格引擎重算/独立代码复算；无可用重算器时明确未重算，关键结果不从不明缓存取数。
- model-audit-tieout的静态脚本是问题线索，不是自动裁决：本次模板冒烟中普通内部单元格公式被标外部引用，折现期指数被标硬编码。逐项查看原公式、来源及经济影响，保留已证实误报的解释；其余项不能批量忽略。静态检查不重算公式、不核实来源，不因退出码0便宣布模型通过。
- Excel/HTML为估值附属交付，不改变主报告六部分顺序；复用用户已明确的语言、深度和范围，支持模块不重复询问已解决偏好，也不读取未授权账户/私人消息。按目标技能要求检查可视化及来源定位后再交付。
- Investment Banking只在符合其交易入口政策时进入。控制权价值、交易协同及买方融资案例与普通少数股东价值分开，不把这些模块称拿到了外部投行研报。投行公开观点仍在独立估值后最后参考。

顺序：财务标准化/经营假设 → 选方法并实际计算/建模 → 必要的模型审计和差异修复 → AIVA报告编辑 → 主插件最终证据核验与独立复核 → 交付。模型审计和独立复核各自有明确范围，任何插件的通过标签均不能覆盖主插件FAIL/INCOMPLETE。只问插件整合时不跑真实公司研究；恢复旧研究不重跑或修改已有估值，除非用户本次明确要求。
