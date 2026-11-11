# LangGraph 正式辩论调度

完整研究的四位研究员完成取证后，Leader 准备争点和中性材料，由 LangGraph 接管多空阶段。两位辩手使用不同的 Codex 会话。完成并校验双方开篇后才交换原文，收齐双方质询后才转发给原辩手作答。辩手可按争点请求指定材料。调度器从已登记的本地文件中提取原文，记录结果并交独立复核。复核要求补答时，调度器将具体问题发回原辩手，完成一轮定向修订并再次复核。仍有重大问题则暂停正式交付。

## 准备与执行

使用 Python 3.12，安装[固定版本依赖](langgraph-requirements.txt)，并用已登录的 Codex CLI 执行。项目通常已有 `.runtime/langgraph/bin/python`，否则在工作区创建隔离环境：

```sh
python3.12 -m venv .runtime/langgraph
.runtime/langgraph/bin/python -m pip install -r "<skill>/references/langgraph-requirements.txt"
```

1. 使用现有 `init`、`progress-start` 和角色登记完成 `research` 阶段。保留共用的 `debate-basis.md`，避免提前派出辩手。
2. 在运行目录创建 `debate-brief.json`。 `facts` 为截至研究日的中性事实和来源定位，包含计量口径和已知缺口。 `issues` 为数组，每条含 `dispute_id` 和 `topic`，正式报告至少两个重大争点。 `sources` 为按来源 ID 索引的对象，每项含运行目录内的 `path`、简短 `description` 和 1 起算的 `first_line`、`last_line`。开篇只收到 `facts` 和 `issues`，其中排除 Leader 的模型基准、目标价和已有结论。来源目录可含已保存的原文或研究员摘录，描述明确标记各自类型。将报告语言写入 `output_language`（如 `English` 或 `Simplified Chinese`），调度器会把它传给每个辩手及复核轮次。旧底稿省略此字段时沿用简体中文。
3. 运行以下命令，打开运行目录的 `progress.html`。中断后使用同一命令并加 `--resume`。继续沿用检查点中的角色身份和已收到的产物。记录失败原因，修复后只恢复未完成工作。

```sh
.runtime/langgraph/bin/python "<skill>/scripts/research_run.py" graph-debate --run "<运行目录>"
```

Codex 执行器明确使用 OpenAI 提供方和登录状态，以只读方式运行。补证只从当前运行目录登记的来源读取。两位辩手各三轮，复核最多两轮，每位被退回的辩手最多补答一次。首轮真实验收可使用一个小范围争点。

`cross-examination.md` 展示原始交锋，`debate-transcript.json` 提供正式 `challenges.json` 所需的问答。补证和每次独立复核另存为 `debate-evidence.json`、`debate-review-pass-*.json`。面板随实际执行事件更新。成功后进入估值，财务角色、Leader 和正式交付复核继续按现有要求登记。辩论通过只验收当前争点与问答，正式报告仍须复算并取得整稿复核。

恢复既有手工辩论沿用原检查点。遇到执行器无法使用时，由 Leader 报告原因，按实际状态选择恢复当前辩论或另起手工流程。

## English setup

Use Python 3.12 with the pinned dependencies above and a signed-in Codex CLI. Complete the four research roles before dispatching the graph. In `debate-brief.json`, provide neutral `facts`, `issues` with a `dispute_id` and `topic` per issue, and `sources` keyed by source ID. Each source points to a run-relative `path` and includes a `description` and one-based `first_line` and `last_line`. Set `output_language` to `English` for English debate prose. Quotations stay in their source language. Run the same `graph-debate` command above, adding `--resume` to continue the existing checkpoint. Use the transcript and independent review when moving into valuation and final delivery.
