# 团队调度与研究进度

适用于完整公司研究。用户给出公司名或代码后，主代理担任 Leader，在 Codex 中使用真实子代理工具派工。公司概况和财报专项沿用各自入口。已完成的旧报告保持原有交付和复核记录。

## 立项与面板

在运行目录初始化之后，用项目规定的时区启动面板。没有项目时区时用 UTC。

```bash
python3 <skill>/scripts/research_run.py progress-start --run <目录> --question '本轮要回答的具体问题' --next '第一个取证或派工步骤' --timezone Asia/Hong_Kong
```

立即把 `progress.html` 的绝对路径作为可点击链接发到主聊天，并说明用本地浏览器打开后每 5 秒读取状态；面板显示最近登记的时间。面板和主聊天都使用有来源或行动的进展，例如发现一个口径差异、补查一项竞争证据、因此调整一项估值情景。仅当状态有意义地变化时更新主聊天。当前阶段、角色数、工作描述和时间线取自 Leader 已登记的运行事件。

Leader 是唯一的状态写入者。子代理只写分配给自己的文件，向 Leader 回报首个有意义的取证进展、关键发现、阻塞和完成情况。Leader 收到回报时更新面板。并行等待期间采用可在角色回报时唤醒的等待方式，收到阶段进展就登记后继续。进度只写适合交给读者的工作摘要、来源线索和下一步，避免敏感资料、凭证及内部推理文本。

```bash
python3 <skill>/scripts/research_run.py progress-stage --run <目录> --stage research --note '已确认的研究范围或阶段产出' --next '下一项任务'
python3 <skill>/scripts/research_run.py checkpoint --run <目录> --role <角色ID> --status running --agent-id <真实ID> --note '这一角色实际收到的具体任务'
python3 <skill>/scripts/research_run.py progress-event --run <目录> --role <运行中的角色ID> --note '已收到的可公开证据发现'
python3 <skill>/scripts/research_run.py progress-event --run <目录> --note '为什么调整方向' --question '调整后的主问题' --next '将采取的行动'
```

每位角色启动时写清具体问题和首个要查的材料，不能共用笼统派工备注。只在实际创建或唤醒后记为运行，收到产物后用相同 ID 和实际文件记为完成。待派工角色留在队列。多空开篇交回后如果智能体已退出当前轮，先用同一 ID 登记 `waiting`，转交质询并实际唤醒后再登记 `running`。任务启动失败或角色返回阻塞时登记失败原因、已有文件和后续行动。重试前确认旧任务已停；受同一额度或权限阻塞最多尝试恢复一次。

## 阶段和交接

1. **research**。按可用并发席位分批启动四个研究角色。每位独立完成首轮底稿再共享，Leader 负责及时释放已结束的席位。四份检查点有效才进入辩论。
2. **debate**。新研究默认按[LangGraph 正式辩论调度](langgraph-debate.md)准备中性材料并执行 `graph-debate`。调度器执行[多空辩论验收标准](debate-standard.md)的独立开篇、原文质询和逐条答复，根据辩手请求补证，按独立复核意见定向退回。等待调度器成功交接到 `valuation` 后，再复算与写裁决。原有手工辩论沿用原检查点，由 Leader 运行 `debate-ready` 确认每次转发。
3. **valuation**。让财务角色重算受裁决影响的假设，在同一口径下说明情景差异。需要再派该角色时，先登记运行，完成后用更新的财务底稿及模型文件重新登记。Leader 完成六部分报告及 `leader-feedback.md`。反馈写清核心判断、辩论前后变化、未决问题与可验证指标。
4. **review**。新复核员先基于证据及双方原文逐争点作判断，再核对 Leader 裁决、报告及模型。在 `delivery.json` 的 participants 中列齐实际参与的研究、辩论和合稿者。任一争点被独立复核标为 `revise` 时，交付门禁保持阻断。回到 `research`、`debate` 或 `valuation` 定向修订后重新复核。
5. **complete / limited / blocked**。按门禁实际结果登记完成、有限交付或受阻，说明下一步。进入完成或有限交付前脚本会重新核对交付门禁。受阻前先停止或收齐仍在运行的子代理，再登记其结果。只有可交付的两种状态显示正式报告和反馈入口。

恢复时先执行 `resume`，核对文件完整性和宿主实际子代理状态，将中断的角色如实改为失败或待派工，再从面板阶段继续。已完成且未受改动影响的底稿继续复用。已有面板不重复立项。单独重建页面可用 `progress-render --run <目录>`，不会生成研究活动或修改检查点。
