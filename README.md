# AI Berkshire · Codex Community Edition / AI 伯克希尔 · Codex 社区版

[English](#english) · [简体中文](#简体中文)

## English

AI Berkshire is a value-investing research toolkit for Codex environments that support local plugins. It brings together **Berkshire Team 2.2.5**, which organizes company research and checks its evidence, and **AI Value Investing Agents (AIVA) 1.2.1**, which adds analytical and writing guidance. Berkshire Library helps index and search materials in a workspace you choose.

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
```

Restart the ChatGPT desktop app. In the Codex plugin directory, select **AI 伯克希尔 · 社区版** and install Berkshire Team. Install and enable AIVA as well to use joint mode. You can also download the repository and open its root folder in Codex to use the local marketplace. [Official OpenAI installation guide](https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually)

Try asking: “Use Berkshire Team to explain how a company of my choice makes money. Cite your sources.” Core verification scripts use Python's standard library. Some market and earnings features require separately configured data dependencies or connectors. [Plugin details](plugins/berkshire-team/README.md)

### Data, security and licensing

Research outputs, library records and retrieved data are saved in your workspace. Online research uses public sources or data tools you've authorized. Follow each provider's data access and usage terms. Report vulnerabilities privately through GitHub and use Issues for ordinary feedback. [Security policy](SECURITY.md)

This is a community edition derived from [AI Berkshire](https://github.com/xbtlin/ai-berkshire) and [AI Value Investing Agents](https://github.com/FernandoAbishai/ai-value-investing-agents). It is unaffiliated with Berkshire Hathaway and carries no endorsement from the investors or upstream maintainers mentioned. It is for research and education and does not provide investment advice. [MIT license](LICENSE) · [Upstream and third-party notices](NOTICE.md)

## 简体中文

AI 伯克希尔是一套面向支持本地插件的 Codex 环境的价值投资研究工具。**伯克希尔团队 2.2.5** 负责组织公司研究和核对证据，**AI Value Investing Agents（AIVA）1.2.1** 补充分析和写作方法。伯克希尔资料库可在你指定的工作区登记和检索材料。

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

已安装 Codex CLI 时，可运行上面的命令添加本仓库。重启 ChatGPT 桌面应用，在 Codex 插件目录中选择 **AI 伯克希尔 · 社区版** 并安装伯克希尔团队。需要联合模式时也安装并启用 AIVA。你也可以下载源码，在 Codex 中打开仓库根目录，使用本地插件市场。[OpenAI 官方安装文档](https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually)

可以先试「用伯克希尔团队解释我指定的公司怎么赚钱，附上来源」。基础核验脚本使用 Python 标准库，部分行情和财报功能需要另外配置数据依赖或连接器。[插件详情](plugins/berkshire-team/README.md)

### 数据、安全与许可

报告、资料库和取数结果保存在你的工作区。联网研究使用公开来源或你已授权的数据工具。使用数据请遵守各提供方的访问和使用条款。漏洞请通过 GitHub 私密提交，普通反馈可用 Issues。[安全说明](SECURITY.md)

本社区版基于 [AI Berkshire](https://github.com/xbtlin/ai-berkshire) 和 [AI Value Investing Agents](https://github.com/FernandoAbishai/ai-value-investing-agents)，与伯克希尔哈撒韦无隶属关系，也未获文中投资人或上游维护者背书。内容供研究和学习使用，不构成投资建议。[MIT 许可证](LICENSE) · [上游与第三方声明](NOTICE.md)

### Local tests / 本地测试

```sh
python3 -m unittest discover -s plugins/berkshire-team/tests
```
