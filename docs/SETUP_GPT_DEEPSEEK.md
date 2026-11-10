# GPT / DeepSeek installation and usage | GPT 与 DeepSeek 安装指南

[English](#english) · [简体中文](#简体中文)

> This guide documents **how to run the same AI Berkshire Codex plugin with either GPT or DeepSeek**. Installing the plugin and selecting an LLM provider are separate steps. It does not claim that mixed-model subagent orchestration is bundled or verified.
>
> 本指南介绍如何通过 **GPT 或 DeepSeek 运行同一套 AI Berkshire Codex 插件**。安装投研插件与配置底层模型是两件独立的事。当前公开版不保证开箱即用的 GPT + DeepSeek 混合子代理调度。

## English

### What this repository contains

- **Berkshire Team 2.2.6**: four research roles; company and industry analysis; financial data and cash-flow valuation; source/evidence checks; challenges and independent review.
- **AIVA 1.2.1**: optional analytical and writing guidance integrated into the same research workflow rather than running a second duplicate team.
- **Berkshire Library**: local source registration and search, with explicit boundaries between indexed, retrieved, and actually read content.
- **Delivery acceptance (development snapshot)**: machine-checkable statuses `COMPLETE`, `LIMITED`, and `BLOCKED`; required evidence and model inputs; review invalidation when dependent artifacts change; offline CI tests. See [delivery acceptance](delivery-acceptance.md). Passing automated checks does not prove economic judgment or independently validate facts.

Data tools such as Longbridge, AKShare, SEC filings, and earnings integrations are **optional and availability-dependent**. This project does not ship an API subscription, private data, trades, or brokerage account access.

### 1. Install the Codex plugin (shared by GPT and DeepSeek)

Requirements: a supported Codex CLI / ChatGPT desktop Codex setup, internet access for source collection, and Python 3.9+ for basic verification scripts. Some data adapters require separate Python 3.11+ environments and additional packages. A complete multi-agent research run requires genuine subagent support in the host.

Run this in a terminal with Codex installed:

```sh
codex plugin marketplace add goldmansachs687-ctrl/ai-berkshire-codex --ref main
codex plugin marketplace list
```

Restart the ChatGPT desktop app, open the Codex **Plugins Directory**, select the **AI 伯克希尔 · 社区版** marketplace, and install **Berkshire Team**. Install **AIVA** as well if you want joint-mode research. Open a new Codex session to test.

Alternatively, clone the public repository and open its root in Codex; the repo already includes `.agents/plugins/marketplace.json`. Updates to a marketplace source can be obtained with `codex plugin marketplace upgrade`; installing a plugin does not automatically update an existing local working copy.

Reference: [OpenAI's local marketplace guide](https://developers.openai.com/plugins/build/plugins).

### 2A. GPT / Codex route

1. Install/open Codex, and sign in with a ChatGPT account supported by your Codex client.
2. Add the marketplace and install Berkshire Team as in step 1.
3. Keep/select a supported GPT model in Codex. No **DeepSeek** key is needed for this route; subscription and API access are separate billing/authentication methods.
4. Try: **"Use Berkshire Team to research the business model of a company I name. Include primary sources, identify unknowns and do not invent financial data."**

For full-team research, verify that your Codex environment really supports subagents and has sufficient limits. If it does not, the workflow should report the limitation rather than pretending four independent agents worked.

### 2B. DeepSeek route (official Codex integration)

DeepSeek documents a native **Responses API** integration for Codex. Its official setup guide currently lists `deepseek-flash` and `deepseek-v4-pro`, requires Codex **0.164+** for the supplied setup script, and states that the CLI, desktop Codex and IDE extension share the relevant configuration.

1. Obtain a **DeepSeek API key** from the DeepSeek platform; API billing is separate from ChatGPT.
2. Back up your existing `~/.codex/config.toml`, especially when another Codex/DeepSeek task is running.
3. Follow the [official DeepSeek → Codex integration guide](https://api-docs.deepseek.com/quick_start/agent_integrations/codex/). It provides a setup script and a manual configuration reference. Review a downloaded script before running it, particularly because it changes local authentication and provider settings.
4. In the official script choose model option **1** (`deepseek-flash`) or **2** (`deepseek-v4-pro`). The guide documents option **9** for restoring its previous Codex configuration.
5. Restart Codex and confirm which model is selected, then install/use **the same Berkshire Team marketplace** from step 1.

On macOS/Linux, you can *download the vendor script for inspection* rather than executing remote code in one line:

```sh
curl -fsSLo codex-deepseek-setup-en.sh https://cdn.deepseek.com/api-docs/codex-deepseek-setup-en.sh
# Read and verify the script before running:
less codex-deepseek-setup-en.sh
bash codex-deepseek-setup-en.sh
```

On Windows PowerShell, consult the official page for the current `.ps1` script; download and review it before execution. The setup can write the API key into the local Codex configuration. **Never commit `config.toml`, `models.json` with credentials, `.env`, API keys, or private reports to a public repository.** Do not run the setup while relying on an active Codex session's current provider settings.

### 3. GPT + DeepSeek together?

Using the same plugin with either model is straightforward once each provider is configured. **Automatic GPT-main / DeepSeek-worker collaboration is a separate orchestration feature**, not something this repository's marketplace manifest itself sets up. A Codex child agent may inherit its host model; do not infer that a named role is actually backed by a second provider without checking the agent runtime and logs.

If building a mixed-provider workflow, prefer separate Codex profiles/configuration homes or isolated workers, separate Git worktrees for code-writing agents, read-only review where appropriate, and a final GPT-run evidence/model/delivery check. Keep API keys out of the repository and require explicit approval before publishing research or placing trades.

### 4. Check the public source

From a *fresh checkout* of the repository:

```sh
python3 -m pip install -r requirements-ci.txt
python3 scripts/check_plugins.py
python3 scripts/run_tests.py
```

These are offline validation commands; they do not test live brokerage endpoints, third-party model billing, or the runtime independence of agents. For the delivery gate examples, see [the acceptance guide](delivery-acceptance.md).

---

## 简体中文

### 项目特点

- **伯克希尔团队 2.2.6**：按商业模式与护城河、财务及估值、行业竞争、管理层与风险组织四个研究角色；注重一手资料、现金流估值、反证与独立复核。
- **AIVA 1.2.1**：按需补强分析和写作，尽量复用同一研究团队、底稿和模型，避免重复创建两套研究。
- **伯克希尔资料库**：在本地登记与检索资料，明确区分“已索引”“已取得”“实际读过”。
- **统一交付验收（开发快照）**：将研究标为 `COMPLETE`（完整）、`LIMITED`（有限）、`BLOCKED`（不可交付）；检查证据、模型、复核依赖及变更后的复核失效。详见[验收说明](delivery-acceptance.md)。机器核验通过不等于投资结论正确。

长桥、AKShare、SEC 公告、美股业绩数据等属于**按需使用的可选数据能力**，取决于环境、授权及数据覆盖情况。本仓库不提供付费数据权限，不含私密持仓，也不负责自动交易。

### 一、安装插件（GPT 与 DeepSeek 通用）

前提：已安装支持本地插件的 Codex CLI 或 ChatGPT 桌面端 Codex；基础核验脚本需要 Python 3.9+，部分数据环境需要 Python 3.11+ 和额外依赖。完整四角色研究需要宿主实际支持子代理。

```sh
codex plugin marketplace add goldmansachs687-ctrl/ai-berkshire-codex --ref main
codex plugin marketplace list
```

重启 ChatGPT 桌面应用，在 Codex 插件目录找到 **AI 伯克希尔 · 社区版**，安装 **Berkshire Team**；需要联合研究时再安装 **AIVA**。打开新会话试用。

也可以克隆公开仓库并在 Codex 打开根目录，仓库已经包含 `.agents/plugins/marketplace.json`。更新市场源可使用 `codex plugin marketplace upgrade`，但它不会自动替换你自行维护的本地源码。

官方参考：[OpenAI 插件市场与本地安装](https://developers.openai.com/plugins/build/plugins)。

### 二、使用 GPT

1. 安装并打开 Codex，使用支持的 ChatGPT 账户登录。
2. 按第一节安装伯克希尔插件。
3. 在 Codex 选择可用的 GPT 模型即可；这条路线无需 DeepSeek API Key，ChatGPT 订阅与独立 API 计费应分开理解。
4. 试运行：「使用伯克希尔团队分析我指定公司的商业模式，优先引用原始资料，明确数据缺口，不要编造财务数字。」

若环境没有真实子代理能力或额度不足，应明确标记未完成，不能声称四位独立研究员已经分别工作。

### 三、使用 DeepSeek

DeepSeek 官方提供面向 Codex 的 **Responses API** 接入指南，目前列出 `deepseek-flash` 和 `deepseek-v4-pro`。官方配置脚本要求 Codex **0.164 或更新版本**。

1. 从 DeepSeek 官方平台取得 API Key（单独计费）。
2. 备份 `~/.codex/config.toml`，特别是还有 Codex/DeepSeek 任务运行时。
3. 打开 [DeepSeek 官方 Codex 接入教程](https://api-docs.deepseek.com/quick_start/agent_integrations/codex/)，按官方脚本或手动配置说明操作；执行下载脚本前先查看脚本内容。
4. 官方安装菜单中选择 **1**（`deepseek-flash`）或 **2**（`deepseek-v4-pro`）；其文档说明选项 **9** 可恢复原有 Codex 设置。
5. 重启 Codex 并核实当前模型，再按第一节安装、使用同一套伯克希尔插件。

Mac/Linux 的可检查脚本安装示例见上文；Windows 请使用官方文档中的 PowerShell 安装方式，先下载并检查脚本。

**特别注意：** DeepSeek 安装脚本可能修改 Codex 的共享配置与认证方式，也可能将 API Key 保存到本机配置。不要把密钥、`.env`、私人报告上传到公开仓库；不要在当前任务运行期间随意切换全局模型配置。

### 四、GPT 主导、DeepSeek 分担任务

同一套伯克希尔插件可以分别运行在 GPT 或 DeepSeek 模型之上。但**让 GPT 担任主代理、DeepSeek 担任子代理，是额外的多模型编排能力**。仅安装这两个模型或插件，不能证明它们已经自动协同。

后续若配置混合模式，建议分离模型配置/运行环境，为写入型 Agent 分配独立 Git Worktree，DeepSeek 可负责限定任务或只读复核，再由 GPT 统一核对证据、估值和交付状态。必须根据实际代理日志核实调用的是哪个模型。

### 五、验证

从新克隆的仓库根目录运行上文的 `requirements-ci.txt`、`check_plugins.py`、`run_tests.py` 命令。它们验证的是公开源码的离线配置和测试，**不代表**真实证券数据接入、DeepSeek API、GPT+DeepSeek 并发协同已经完成端到端联调。

本项目用于研究与学习，不构成投资建议。公开版保留原项目许可与第三方来源说明。
