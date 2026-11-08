# 美股财报复盘与盈利预期（2.2.1）

本能力根据 Finance Skills 的 earnings-recap、estimate-analysis 思路适配，完整来源与 MIT 许可见插件根目录 THIRD_PARTY_NOTICES.md、licenses/finance-skills-MIT.txt。此处为本插件运行规则，不需另装另一套插件，也不调用其自动 pip 安装指令。

## 何时调用

- 用户只问美股财报表现：读取当期官方财报/业绩公告，以 recap 补充市场 EPS 预期及价格反应。输出简明复盘，无需启动完整四角色团队。
- 用户只问分析师预期、EPS 修正、市场定价假设：用 estimates。它提供的是市场一致预期，不能替代公司指引或我们的长期预测。
- 完整公司研究：财务角色在最新财报和估值需要时调用；独立估值假设先落盘，再看外部预期或目标价。不要每个角色重复拉一遍 Yahoo。
- 长期逻辑不依赖短期预期时可以不调用。公司基本信息→商业模式→十年财务→生意/护城河/文化→多方法估值→外部研报的用户结构优先；预期与财报反应放在相关小节或附录，不抢占正文。

## 可执行入口

先解析本技能绝对目录 <skill> 和实际工作区 <workspace>。适配器复用 `.berkshire/data-runtime.json` 或 `BERKSHIRE_DATA_PYTHON` 指向的隔离 Python 环境；不会读取/输出 SEC 联系身份。基础脚本仍可用 Python 3.9+ 启动。数据依赖见 us-earnings-requirements.txt。

```bash
python3 <skill>/scripts/us_earnings.py --workspace <workspace> doctor
python3 <skill>/scripts/us_earnings.py --workspace <workspace> recap --symbol AAPL --output <run>/data/us-earnings
python3 <skill>/scripts/us_earnings.py --workspace <workspace> estimates --symbol AAPL --output <run>/data/us-estimates
```

doctor 只验证本地环境，不证明联网。每次取数新建带时间和随机ID的目录，保存 bundle.json：原始表格、原始索引/时区、币种提示、软件版本、来源、取数时间、失败与截断。读取完整 bundle 后再写研究；FETCHED 只代表取数完整，INCOMPLETE 表示部分失败/缺失，ERROR 表示查询失败；这些都不是证据核验 PASS。

只接受已核实的美国交易所上市 EQUITY。ADR 必须核对存托比例、EPS 每股口径、交易币种和财报币种。不会把本地代码映射为美股；ETF/OTC 等未覆盖类别保留缺口。

## 财报复盘

1. 从 SEC / 公司 IR 确认财报期间、发布日期、GAAP 与调整后口径；从官方电话会或演示核实指引与分部变化。
2. Yahoo 的 earnings_history 以财季结束日标识，earnings_dates 以事件时间标识，两者不能直接按行号拼接。实际EPS和预期EPS还须验证口径/ADR单位。
3. 收入、利润率和现金变化优先原始财报；相同财季有上年数据才算同比，不将前一季当同比。调整后EPS不得与GAAP EPS直接算超预期；零预期不算百分比，负预期以绝对值作分母并说明。
4. Yahoo 的季度数据通常有限，不能用它替代十年财务。缺少当期收入一致预期时只描述收入增长，不编造收入超预期比例。
5. 股价反应需先核实披露时点与交易日历。默认不推断盘前/盘后，不从午夜时间戳猜测。若已核实，可指定公告前最后收盘和公告后第一个完整常规交易日的日期及官方来源：

```bash
python3 <skill>/scripts/us_earnings.py --workspace <workspace> recap --symbol AAPL --pre-session <YYYY-MM-DD> --post-session <YYYY-MM-DD> --timing-source <已核实的IR或交易所HTTPS链接> --output <run>/data/us-earnings
```

适配器只匹配指定交易日，不拿最近一根K线替代；保守地不计算纽约当天尚未跨日确认的日线。缺收盘返回 PENDING，价格未知保持 null。拆股窗口阻断直接涨跌幅；未复权收盘收益不含股息，也不等于财报的因果贡献。盘中公告需说明 close-to-close 包含公告前交易。

## 一致预期

保存 EPS/收入均值、上下限、分析师数、7/30/60/90日修正及上调/下调数量。分母为零、缺值或缺分析师覆盖时标缺口，不补零。预期标签0q/+1q/0y/+1y随时间滚动；跨快照对比先核实对应实际财季，不能直接按标签相减。

预期分歧、修正方向只描述市场看法，不把“上调比例>0.7”等统一阈值写成买入结论。不因短期股价或一致预期变动自动推翻长期商业判断。

## 数据与历史边界

- 所有 Yahoo 接口统一归为同一来源家族；与 SEC 的转述关系也须核实，不能自动声称独立双源。
- 关键值接入 evidence.json 时保留 metric/period/basis/unit/currency/source/locator/origin_group。事实、市场预期和假设在正文分开；市场预期不能用 kind=assumption 替代历史事实核验，也不能当作已实现盈利。
- 查询是当前快照，只允许当天 as-of。研究历史时使用当时已保存的证据包或明确可追溯的历史供应商资料，不用今天的分析师预期回填过去；保存的财报历史也可能被重列。
- 失败不阻断已有官方资料的公司研究，保留具体缺口即可。Yahoo 不可用时转用本轮已授权来源，不绕过访问限制。
- 不集成 company-valuation 的固定参数、估值混合权重或远期PE×历史EPS示例；估值继续遵循本插件 valuation.md。

交付 earnings-recap.md 或 estimates.md，附原始数据包和少量真正影响判断的变化；详细核验记录放附录。是否已取得官方指引、EPS口径是否一致、是否已完成股价反应各自明确。
