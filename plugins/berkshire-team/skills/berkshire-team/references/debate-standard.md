# 多空辩论验收标准

Leader 先写 `debate-basis.md`，用同一估值日、事实底稿、基准假设和计量单位，确定至少两项可能影响投资判断的分歧。每项是一道可以判对错的题，例如给出具体期间的现金转换率，明确区分已披露事实、估算和预测。此文件在进入 `debate` 时固定。

使用两个不同的真实子代理，三轮均唤醒原角色。Leader 只协调与裁决。每次先向面板登记已收到什么和当前在等什么。所有 `--file` 参数使用研究目录相对路径。

1. **独立开篇。** 只发送共同底稿和争点。两位各写 `bull-opening.md` 或 `bear-opening.md`，逐项给出事实出处、同口径预测、最不利事实和改判阈值。以 `waiting` 登记各自开篇。
2. **提出质询。** 对每位运行 `research_run.py debate-ready --run <目录> --role <角色>`，返回 `questions` 才传对手原始开篇并实际唤醒该代理，随后登记 `running`。各写 `bull-questions.json` 或 `bear-questions.json`，内容为数组，每个重大争点一条，含 `dispute_id`、`target`（对方开篇中可逐字定位的主张）、`question`。优先问能区分两种解释的证据、关键数量级或时间尺度。各用 `waiting` 同时登记自己的开篇和问题文件。
3. **直接答复。** `debate-ready` 返回 `replies` 后，才逐字转发对手的问题，唤醒原代理并登记 `running`。各写 `bull-replies.json` 或 `bear-replies.json`，每个收到的争点一条，含 `dispute_id`、`response`、`concession`、`position_before`、`position_after`、`change_trigger`、`source_locator`。先直接回答，给出证据可区分什么及缺什么，再说明预测有无变化。可以维持分歧。各写最终的 `bull-case.md` 或 `bear-case.md`，以 `complete` 同时登记自己的开篇、问题、答复及最终稿。主代理把问题和答案逐字纳入交付契约；摘要可以另写。

`cross-examination.md` 按争议排出多空预测、双向质询、答复、让步和改判条件。只有双方确实对话后才生成交锋摘要。用面板 `progress-event` 展示最有信息量的一问一答。独立复核开始后如等候超过约两分钟，更新已收到的核验事项或当前等待项，注明没有新结果时的状态。各阶段记录基于真实工具事件。

`debate-ruling.md` 逐项说明哪条证据改变了什么判断。分开写双方原预测、答复后的预测、Leader 采用的假设、被拒绝的推断和会改判的观测。证据区分不了两种解释时，标 `unresolved`，保留情景和验证条件。财务角色在同一模型固定其余输入，复算基准和挑战值，给出一项现金额或每股估值影响。长期争议另列持续路径。若主张涉及现金转化，说明测算的是收入增长对集团估值的敏感度，还是已取得独立利润与再投资证据。

由未参与前序研究和合稿的代理先读原始证据、开篇、问题和答复，要求其先形成逐项判断，再给它 Leader 裁决与模型核对。复核员自行选择每个争点最强的一手证据和反证，检查答复是否击中问题，说明证据是否支持基准变更并独立复算至少一项关键对照。把结果逐项写进 `review.json.debate_judgments`，字段为 `dispute_id`、`strongest_evidence`、`directness`、`independent_judgment`、`assumption_impact`、`decision`（`accept` 或 `revise`）。发现回避、无依据的改判或错误的估值传导，写清需要补答或重算的具体点并标 `revise`。门禁会阻断交付。回到对应阶段，原辩手可在最终稿补写定向追问答复，保留首次问题和原始答复记录；修订后重新独立复核。

`challenges.json` 保持原字段。每项 material disagreement 新增：

- `id` 唯一短标识。原 `question`、`material: true`、`status: "resolved"`、`resolution`、`evidence` 继续保留。此处 resolved 指 Leader 已处理，即使证据暂不裁定事实。
- `metric` 含指标、期间和单位。 `bull`、`bear` 为不同的可检验预测。 `test` 写明观察阈值和期限。 `verdict` 为 `update`、`retain` 或 `unresolved`。
- `decisive_evidence` 写明使 Leader 改判或保留基准的具体证据和边界。`adopted_input` 是最终采用的数值字符串，采用模型单位。保留基准或暂未决时等于基准输入，更新时等于受控对照中复算过的采用值。
- `impact_unit` 为 `cash` 或 `per_share`，分别表示现金额和每股价值。把币种、规模和期间写入裁决。对照的被解释量必须是对应的现金或每股价值，收入等中间量可以附列。
- `base_check`、`counter_check` 为 `valuation-manifest.json` 中两条唯一的检查名称。两条使用同一表达式和相同变量集合，只有 `driver` 指定的变量取值不同，预期输出各自对应模型输出的不同字段。各争议使用各自的检查对。
- 每条 `questions` 记录新增 `dispute_id`、`from`、`to`、`concession`。方向为 `bull` 或 `bear`，每个争点各一条。逐字保留双方提交的 `question`、`response`、`concession`。 `evidence` 必含发问方开篇和答复方最终文件。

三轮交接及逐争点复核适用于协议 4 及以后。已有研究按原协议恢复。脚本核对提交顺序、原文和模型对照，独立复核负责判断论证是否成立。

进入独立复核前，阶段命令会预跑争点与模型对照。先纠正对照错误，再把产物交给复核员。交付检查输出逐项输入、输出及差额，便于与正文核对。
