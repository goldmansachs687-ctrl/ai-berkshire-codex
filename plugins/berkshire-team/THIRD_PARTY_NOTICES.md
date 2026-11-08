# 来源与修改说明

来源：https://github.com/xbtlin/ai-berkshire
上游提交：258578ac446cbca11a90905e0d5fdfd0a9492127
上游许可：MIT，Copyright (c) 2026 xbtlin，完整文本见 LICENSE。

本地插件改编自 investment-team 研究流程，重新编写 Codex 单入口、任务调度、角色说明、数据核验规范和报告结构。以下工具保留上游内容：
- skills/berkshire-team/scripts/financial_rigor.py
- skills/berkshire-team/scripts/report_audit.py
- skills/berkshire-team/scripts/terminal_value.py

本包是个人本地适配，非上游官方发布插件，也非伯克希尔哈撒韦公司出品或背书。

## Finance Skills supplement (2.2.1)

来源：https://github.com/himself65/finance-skills
核查提交：a0850786e72aa23b92862f9f1635b0de506fe206（2026-10-25）。
参考模块：plugins/market-analysis/skills/earnings-recap 与 estimate-analysis。
Copyright (c) 2025 Alex Yang；MIT全文见 licenses/finance-skills-MIT.txt。

本地改编为 references/us-earnings.md 与 scripts/us_earnings.py：保留原始数据，使用项目隔离环境，阻断历史预期回填，显式验证美股与交易日，缺失/零值/负EPS和失败状态分开。没有复制其全套插件或自动依赖安装行为；company-valuation模块未整合。来源文件指纹见 references/finance-skills-provenance.json。

yfinance（https://github.com/ranaroussi/yfinance）是单独安装的Apache-2.0外部依赖，未捆绑进插件。Yahoo数据为非官方聚合来源，所有接口不构成独立双源；数据使用条件与代码许可分别适用。

## Optional installed data dependencies (2.1)

AKShare (https://github.com/akfamily/akshare) and EdgarTools (https://github.com/dgunning/edgartools) are MIT-licensed external dependencies installed separately, not vendored in this package. Their full license texts are included in the installed distributions. Upstream data terms and SEC access requirements remain applicable. Tested direct versions are pinned in skills/berkshire-team/references/market-data-requirements.txt.
