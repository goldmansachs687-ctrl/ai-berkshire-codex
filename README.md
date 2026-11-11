# AI Berkshire · Codex Community Edition / AI 伯克希尔 · Codex 社区版

[English](#english) · [简体中文](#简体中文)

## 万事达卡（MA）实跑样例 / Worked example

这次研究在 **2026 年 11 月 10 日（香港时间）**用本地 2.2.8 完成。面板共记录 **27 条事件**。下图按原始记录回放了 **20:17:33** 的交锋阶段。四位研究员已经交卷，两位辩手各自提交了开篇，正在回答对方的质询，独立复核员随后进场。

![万事达卡实跑面板回放。四位研究员已完成，多空两位辩手在回答质询，独立复核员待开始。](docs/examples/mastercard-progress.png)

这轮从 **20:02** 独立取证，**20:14** 进入多空辩论，**20:21** 开始独立复核，**20:26** 附限制交付。以上均为香港时间。

| 争点 | 质询后怎么改判 | 同一模型的受控比较 |
|---|---|---|
| **第五年网络返利率** | 多方追问，Capital One 的局部交易迁移为何能推导全球返利率升到 **57%**。空方接受证据不足，把 **57%** 降为压力情景。多方也承认 Apple Card 留任的合同条款未知，按原交易量测算返利冲击。 | 基准保留 **54.5%**。只把第五年返利率提高到 **57%**，DCF 从 **468.28** 降至 **465.67 美元/股**。 |
| **首年增值服务净收入增速** | 空方拿不出支持 **11%** 的产品或客户披露，接受 **15%** 作为有条件的收入基准。双方把现金兑现列为单独观察项。 | 只把首年服务增速从 **15%** 降到 **11%**，DCF 从 **468.28** 降至 **460.46 美元/股**。 |

**独立复核判为附限制可用（LIMITED）。** 复核员抽查了 **13 组事实**，包括正式收盘价、股数，以及设备和软件资本开支。用单独编写的计算代码复算 **438 项，全部通过**。公开披露缺少增值服务独立营业利润率，交付适用于集团层面的条件估值。

In this completed 2.2.8 run, four researchers handed off to two debaters before a separate reviewer joined. The replay shows both sides answering cross-examination. The bear moved a 57% rebate rate and 11% services growth into stress cases, while the bull acknowledged that the Apple Card terms were unknown and kept transaction volume fixed for the rebate test. Testing each driver separately took the base DCF of **$468.28 per share** to **$465.67** and **$460.46**, respectively. The reviewer passed **438 independent calculations** and limited delivery to group-level conditional valuation because standalone services margins were unavailable.

## English

AI Berkshire helps you research a company in Codex, from understanding how it makes money to checking what could change its valuation. Give it a company name or ticker. The full workflow uses four specialist roles, builds a source-backed financial record, and produces a report with evidence, valuation assumptions, and open questions.

This repository distributes **Berkshire Team 2.2.9** and **AI Value Investing Agents (AIVA) 1.2.1**. AIVA can supplement the analysis and writing in the same research team. Berkshire Library indexes materials in a workspace you choose.

### Full research in 2.2.9

- **One lead, seven subagents.** The lead coordinates four researchers, two debaters, and an independent reviewer. The researchers cover the business and its moat, financials and valuation, industry and competition, and management and risk.
- **Bull and bear cross-examination.** Both sides start from the same evidence and submit independent opening cases before exchanging questions and replies. The lead records what changed and what would change the judgment again. Each material dispute is tested by changing one assumption in the same model and measuring the effect on cash flow or per-share value.
- **A progress panel during research.** The local panel shows each role’s current task, recorded findings, next steps, and completed work. It updates as the lead records events, and saved work can be reused after an interruption.
- **A separate review and a delivery decision.** An independent reviewer checks the evidence, valuation model, and strongest counterarguments. The delivery check distinguishes complete, limited, and blocked work. The final package includes the report, debate record, and the lead’s feedback.

An earlier local build ran all seven subagents through independent review. This release was checked offline. DeepSeek through Codex CLI reached parallel research in a partial test. Full delivery with DeepSeek has yet to be verified. Third-party API providers bill separately for usage.

### How the research works

A full study starts with a company or ticker and a research cutoff date. It builds an independent view of the business and its value before looking at analyst opinions.

1. **Establish the facts.** Identify the company, its history, management, ownership and operations. Use background sources to orient the research, then verify material facts in company filings, exchange disclosures or other primary sources.
2. **Explain how the business makes money.** Identify who pays, what they buy, why they come back, and which costs and investments grow with revenue.
3. **Reconstruct the financial record.** Aim for ten years of comparable financials and link to original filings where available. Label each period, currency and unit. Explain changes in accounting or business scope, and mark gaps.
4. **Challenge the business case.** Four roles cover the business and its moat, financials and valuation, industry and competition, and management and risk. They develop independent findings, compare evidence, and examine what could invalidate the main judgment.
5. **Estimate value under different assumptions.** Link reported earnings to cash available to shareholders. Compare methods suited to the business, such as discounted cash flow and sum-of-the-parts. Explain why estimates differ, what the current price implies, and which assumptions would change the conclusion.
6. **Review and report.** When AIVA is enabled, the same team uses it to improve the explanation. A separate reviewer checks the final evidence and model when the environment supports independent review. The report ends with outside research and distinguishes full reports, public summaries and rating actions.

**Example.** If a subscription company's revenue rises while cash generation weakens, the team checks whether growth came from more customers, higher prices or acquisitions. It then tests whether retention and cash collection support the reported growth, and compares valuations under stronger and weaker retention assumptions. The report shows which evidence would change the judgment.

A company overview or earnings recap can run on its own. Full team research requires internet access and subagent support. [Detailed team workflow](plugins/berkshire-team/skills/berkshire-team/SKILL.md) · [Joint Berkshire + AIVA mode](plugins/berkshire-team/skills/berkshire-team/references/joint-mode.md)

### Install and try

With the Codex CLI installed, add this repository as a plugin marketplace.

```sh
codex plugin marketplace add goldmansachs687-ctrl/ai-berkshire-codex
codex plugin add berkshire-team@berkshire-community
```

If you already added the marketplace, run `codex plugin marketplace upgrade berkshire-community` before running the install command again. Open a new Codex session after installing. For joint mode, also run `codex plugin add ai-value-investing-agents@berkshire-community`. You can also install from **AI 伯克希尔 · 社区版** in the desktop plugin directory. [Official OpenAI installation guide](https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually)

For a full study, try “Use Berkshire Team to research Mastercard (MA).” For a quick overview, ask “Explain how Mastercard makes money and cite your sources.” Core verification scripts use Python's standard library. Some market and earnings features require separately configured data dependencies or connectors. [Plugin details](plugins/berkshire-team/README.md)

### Data, security and licensing

Research outputs, library records and retrieved data are saved in your workspace. Online research uses public sources or data tools you've authorized. Follow each provider's data access and usage terms. Report vulnerabilities privately through GitHub and use Issues for ordinary feedback. [Security policy](SECURITY.md)

This is a community edition derived from [AI Berkshire](https://github.com/xbtlin/ai-berkshire) and [AI Value Investing Agents](https://github.com/FernandoAbishai/ai-value-investing-agents). It is unaffiliated with Berkshire Hathaway and carries no endorsement from the investors or upstream maintainers mentioned. It is for research and education and does not provide investment advice. [MIT license](LICENSE) · [Upstream and third-party notices](NOTICE.md)

## 简体中文

AI 伯克希尔在 Codex 里做公司基本面研究。给出公司名或股票代码，团队从「公司怎么赚钱」查起，整理有来源的长期财务，再回答「哪些事实会改变估值和判断」。报告附有证据、估值假设和待核实的问题。

**本仓库可安装伯克希尔团队 2.2.9 和 AI Value Investing Agents（AIVA）1.2.1。** 启用 AIVA 后，由同一支团队使用它补充分析和写作。伯克希尔资料库可在你指定的工作区登记和检索材料。

### 2.2.9 完整研究流程

- **一位负责人调度七个子智能体。** 四位研究员分别查商业模式与护城河、财务与估值、行业与竞争、管理层与风险。两位辩手负责多空交锋，最后由一位独立复核员检查报告。
- **多空直接质询。** 双方基于同一批证据独立提交开篇，再互相提问和答复。负责人记录哪些判断发生了变化、什么新事实会让双方改判。重大争议在同一个模型里只改一项假设，复算对现金流或每股价值的影响。
- **研究进行中可看进度。** 本地面板展示各角色正在查什么、已登记的发现、下一步和已完成底稿。负责人记录新事件后，面板更新。研究中断后可以从已有底稿续做。
- **复核后明确能否交付。** 独立复核员检查证据、估值模型和最强反证。交付检查区分完整交付、附限制可用和受阻，最终交付报告、辩论记录和负责人反馈。

较早的本地版本已让七个子智能体完成研究和独立复核。本次发布经过本地离线检查。DeepSeek 通过 Codex CLI 接入并跑到并行取证阶段，端到端交付尚未验证。第三方 API 按用量单独计费。

### 研究怎么做

完整研究从公司名称或股票代码、研究截止日开始。团队先对公司和价值形成独立判断，最后才看外部机构的意见。

1. **确认公司事实。** 弄清公司主体、发展历史、管理层、股权和业务范围。先用背景资料了解脉络，再用公司财报、交易所公告等一手来源核实关键事实。
2. **讲清公司怎么赚钱。** 说明谁付钱、买什么、为什么会继续买，以及收入增长会带来哪些成本和再投资。
3. **还原长期财务。** 尽量整理十年可比财务数据，并附可取得的原始财报链接。标明期间、币种和单位，解释会计口径或业务范围的变化，注明缺失数据。
4. **质疑投资逻辑。** 四个角色分别看商业模式与护城河、财务与估值、行业与竞争、管理层与风险。先各自形成判断，再对照证据，找出什么可能推翻主要结论。
5. **比较不同假设下的价值。** 从账面利润推算股东可获得的现金，选用适合公司的方法，例如现金流折现或分部估值。解释结果为什么不同、当前股价反映了什么预期，以及哪些假设会改变结论。
6. **复核并写成报告。** 启用 AIVA 后，由同一团队用它改善分析表达。环境支持独立复核时，再由独立复核者检查最终证据和模型。报告最后参考外部研究，区分原始全文、公开摘要和评级行动。

**举个例子。** 如果一家订阅公司的营收上升，但现金流变弱，团队会先查增长来自新增客户、提价还是收购，再看续费和回款能否支撑这部分增长，最后比较高续费和低续费情景下的估值。报告会写清楚什么证据出现时，原来的判断需要调整。

只查公司概况或复盘财报时，可以单独运行对应流程。完整团队研究需要联网和子代理能力。[团队研究规范](plugins/berkshire-team/skills/berkshire-team/SKILL.md) · [伯克希尔与 AIVA 联合模式](plugins/berkshire-team/skills/berkshire-team/references/joint-mode.md)

### 安装和试用

已安装 Codex CLI 时，运行上面两条命令即可添加市场并安装伯克希尔团队。已添加过市场的用户先运行 `codex plugin marketplace upgrade berkshire-community`，再重新执行安装命令。安装后开启新的 Codex 会话。需要联合模式时，再运行 `codex plugin add ai-value-investing-agents@berkshire-community`。也可以在桌面版插件目录的 **AI 伯克希尔 · 社区版** 安装。[OpenAI 官方安装文档](https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually)

完整研究可以试「用伯克希尔团队研究万事达卡（MA）」。只想看公司概况，可以问「万事达卡怎么赚钱？请附来源」。基础核验脚本使用 Python 标准库，部分行情和财报功能需要另外配置数据依赖或连接器。[插件详情](plugins/berkshire-team/README.md)

### 数据、安全与许可

报告、资料库和取数结果保存在你的工作区。联网研究使用公开来源或你已授权的数据工具。使用数据请遵守各提供方的访问和使用条款。漏洞请通过 GitHub 私密提交，普通反馈可用 Issues。[安全说明](SECURITY.md)

本社区版基于 [AI Berkshire](https://github.com/xbtlin/ai-berkshire) 和 [AI Value Investing Agents](https://github.com/FernandoAbishai/ai-value-investing-agents)，与伯克希尔哈撒韦无隶属关系，也未获文中投资人或上游维护者背书。内容供研究和学习使用，不构成投资建议。[MIT 许可证](LICENSE) · [上游与第三方声明](NOTICE.md)

### Local tests / 本地测试

```sh
python3 -m pip install -r requirements-ci.txt
python3 scripts/check_plugins.py
python3 scripts/run_tests.py
```
