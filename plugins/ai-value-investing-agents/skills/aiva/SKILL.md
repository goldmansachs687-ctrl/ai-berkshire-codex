---
name: aiva
description: "Use when the user explicitly requests AIVA or the Fernando edition for investment research. Full company studies default to joint Berkshire mode in English and Chinese. 用户显式选择 AIVA 时使用，完整公司研究默认联合伯克希尔。"
---

# Fernando 分支 · 本地 Codex 入口

本插件提供基于上游1.2.0的22个研究技能。以本文件所在目录的上两层为插件根目录；`skills/<名称>/SKILL.md` 是已安装工作流，`skills/<名称>.md` 是上游规范源，`tools/` 为配套工具。先解析真实绝对路径，不要求固定家目录、原始clone位置或其他全局skill。

用户没有公司名时只询问公司；公司明确则执行，不重复请求启动确认。默认美股，工作区AGENTS.md及用户六部分报告顺序优先。不恢复用户暂停的研究，除非本次明确要求恢复该研究。

## Language and routing / 语言与路由

Use the requested output language or, if unspecified, the language of the request. Determine scope from intent in both languages. Forward the original request, scope and output language to Berkshire Team for joint studies. In AIVA-only mode, apply the same selected workflow, evidence requirements and review criteria in both languages. The local output-language rule takes precedence over language defaults in bundled upstream skills. Retain source quotations verbatim. “Use AIVA to research Mastercard” and「用 AIVA 研究万事达卡」both request a full study. “Use AIVA to recap Mastercard’s earnings” and「用 AIVA 复盘万事达卡财报」both request an earnings recap.

优先按用户指定的语言交付，否则沿用提问语言。中英文均按任务意图选择范围。联合研究把原始请求、范围和输出语言交给伯克希尔团队。显式只用 AIVA 时，两种语言共用对应工作流、取证要求和复核标准。本入口的语言规则优先于随包上游技能的默认输出语言。原文引语保留原语。

## 完整公司研究默认联合原伯克希尔

用户未明确“只用AIVA/Fernando”时，完整公司研究由已启用的 `berkshire-team` 唯一调度。先从当前插件信息定位它的实际技能路径；宿主未提供时运行只读 `codex plugin list --marketplace berkshire-community --json`，在 installed 中精确匹配name，核对installed/enabled为true及local source.path中plugin.json的name/version相同，再读取其 `skills/berkshire-team/SKILL.md` 与 `references/joint-mode.md`。不要猜缓存路径或使用全局同名skill。

主插件须为支持联合模式的2.2.4或后续兼容版本且joint-mode.md确实可读；把本次用户要求和本插件真实根路径交给该入口，随后由它读取本包investment-memo-craft原模块。不得先启动本包investment-team，不重复创建团队/研究目录，不再回调本aiva入口。共享主插件取数、证据、估值、核验及用户偏好。

主插件不可用、不兼容或读取失败时，明确未联合、记录原因，沿用下方独立AIVA流程，不自动安装/升级；用户明确只接受联合时保留待办而不冒称完成。只问插件、专项任务和恢复旧研究均不因此自动展开完整团队。

## 显式独立或专项调用

按用户任务读取一个主工作流：完整团队 `investment-team`，单公司研究 `investment-research`，财报 `earnings-review`，初筛 `investment-checklist`，管理层 `management-deep-dive`，报告表达 `investment-memo-craft`；其余从随包skills目录按需选择，不能一口气展开全部流程。

使用工作流时按以下真实Codex运行规则映射其客户端操作，其他分析规则按原文保留：

1. 联网检查使用当前会话实际搜索/网页读取工具和一次实际只读检索；不能用`.claude/settings.local.json`是否存在判断Codex权限，不改变沙箱/审批设置。子代理也要报告自己是否成功取证。
2. TeamCreate/Task/SendMessage等映射到当前原生子代理与消息工具。最多按宿主可用席位调度，主代理+三个角色先运行，释放席位后完成第四角色；不假装四角色同时运行。没有代理工具时明确缺口。
3. 当前模型设置继承，不另行指定模型，不创建额外用户聊天或外部付费推理调用。任务产物在当前工作区reports/aiva/下新建唯一目录，工具从本插件根目录用绝对路径调用；保留已有报告。
4. 已安装研究工具不代表其所有可选数据依赖已经安装。先看具体依赖和实际能力，不运行本包安装脚本去覆盖全局skills；用现有授权连接器/公开材料取数，新增依赖按任务范围处理。
5. 优先独立完成分析再参考外部目标价；保留事实、假设、原始来源、财年及币种。工作流自己的审计结果只说明其核验范围，不证明投资回报或模型假设。
6. 安装/介绍插件不是公司研究，不运行样例团队。用户资料、账户、自选修改和对外发布须按本次任务授权，不由技能示例自动执行。

上游SKILL.md保持原样；上述规则是本地宿主适配，并非上游已修复这些问题。来源提交见根目录UPSTREAM.json。
