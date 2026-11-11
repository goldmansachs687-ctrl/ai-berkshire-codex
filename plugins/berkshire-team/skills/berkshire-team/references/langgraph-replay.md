# LangGraph 离线回放

回放已有完整研究的交接和验收。LangGraph 校验四份既有底稿，两位辩手的独立开篇分别通过校验后才汇合。随后核对质询答复和单变量估值对照，最后用交付门禁复查已有独立复核。回放使用原研究的数据和复核记录，零模型调用。完整公司研究由 Codex 调度研究角色。

使用 Python 3.12 建立独立环境，安装[固定版本的依赖](langgraph-requirements.txt)。以下命令中的 `<skill>` 是本技能目录的绝对路径。

```sh
python3.12 -m venv .runtime/langgraph
.runtime/langgraph/bin/python -m pip install -r "<skill>/references/langgraph-requirements.txt"
.runtime/langgraph/bin/python "<skill>/scripts/research_run.py" graph-replay \
  --source "<原研究目录>" --output "<新的回放目录>" --pause-before-review
.runtime/langgraph/bin/python "<skill>/scripts/research_run.py" graph-replay \
  --resume --output "<同一个回放目录>"
```

输出目录位于原研究之外。打开 `progress.html` 查看回放进展与暂停原因。`replay-result.json` 包含对照结果和交付判定，`langgraph.sqlite3` 保存断点。需要一口气跑完时省略 `--pause-before-review`。缺少原始开篇时，流程会等待对应文件，恢复后须通过原指纹校验。原 `run.json` 已变更时应新建回放。
