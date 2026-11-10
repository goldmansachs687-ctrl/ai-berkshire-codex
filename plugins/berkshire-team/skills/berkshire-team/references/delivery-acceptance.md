# 统一交付验收

先判规则，再执行：

- **COMPLETE / 0**：声明的研究类型适用流程全部完成，实质底稿及质询/分歧处置记录齐全；当前 evidence gate 为 PASS；有定量估值时模型、关键输入、结果和可复算检查齐全；独立复核绑定当前全部必要依赖。
- **LIMITED / 2**：同样满足流程、最低证据、模型和当前独立复核要求。仅允许客观不可得且未用于结论或模型的数值缺口。保留原必要证据项（`reported_value=null`），逐项记录尝试来源、影响、禁止结论，并在报告披露。允许的 evidence INCOMPLETE 原因仅为 `reported value unknown`，且该事实无已取得的观测值。若已记录观测值，须先核对和处理，不能以清空报告值来放行冲突。至少一项最低事实经原 gate 通过，全部用于结论和模型的事实必须通过。报告和复核须明确同意 LIMITED 范围。
- **BLOCKED / 1**：任何流程、依赖、格式、独立性或复核有效性错误；证据 FAIL、空证据、缺最低事实、未经支持的关键数字、必要模型/输入缺失、未处置重大冲突、复核过期。不能把 FAIL 改称有限交付。

原 evidence_gate.py 的 PASS/FAIL/INCOMPLETE 与退出码 0/1/2 不变。统一入口只读，不替研究者或复核者完成工作，不刷新复核摘要。缺少新增交付契约的旧研究仍可使用旧 init/checkpoint/resume 命令，但不自动获得交付资格。

## 数据契约

在研究目录新增 `delivery.json`（schema_version=1）：`research_type` 为 `full`（包含估值的完整公司研究）或 `qualitative_brief`；`applicable_roles` 为角色 ID 列表，full 必须四角色齐备，brief 须填写 `scope_reason`；`participants` 列出包含作者、协调者、模型作者在内的实际研究者；`minimum_claims`、`conclusion_claims` 列出最低事实和结论所依赖事实；`challenges` 指向质询 JSON；`valuation` 含布尔值 `required` 和需要时的 `manifest`；`limitations` 为缺口数组；`dependencies` 可补充必要文件。

质询 JSON 包含非空 `questions`（question/response/evidence 文件列表）及 `disagreements`（每项 material/status/resolution/evidence）。质询、答复和分歧处理说明须为去掉首尾空白后仍非空的文本。没有分歧须保留 `no_material_disagreements_reason`。重大分歧必须 resolved 且有处置依据，不能只写 done。

有估值时，manifest 包含非空 `models`、`inputs`、`outputs` 文件列表，`reproduce` 复算说明，`key_inputs`（file/pointer，事实用 claim_id，假设用 rationale）及 `checks`。检查使用受限十进制算术表达式（+ - * / **，整数指数最多100），variables 映射到输入 JSON 的 file/pointer；expected 指向输出 JSON；absolute_tolerance 不得超过 0.000001。不执行模型代码或命令。每个关键输入都必须参与复算检查，历史输入必须匹配经 gate 通过的事实，假设必须在 evidence 中明确登记为 assumption。支持 JSON/CSV/Python 等可审阅文本产物；现有文本模型无需改格式，用 manifest 适配。二进制模型/原件应先导出文本、公式与输入输出，未支持的文件格式会阻断而不会静默放过。检查保证声明范围的算术与输入引用，不能证明模型经济合理性或所有代码路径。

`review.json` 含 reviewer_id、decision（COMPLETE/LIMITED）、非空 checks，逐项覆盖 workflow/evidence/model/scope/counterevidence，及 limitations 中 claim_id 的 acknowledged_limitations。`review.md` 保存具体复核论证。完成实际复核后才运行原 checkpoint 命令；有 delivery.json 时自动扩展必要依赖并记录 SHA-256 清单和研究状态语义摘要。

JSON 文件路径相对研究目录，Markdown 链接相对当前 Markdown 文件。允许解析后仍在研究目录内的上级引用，禁止越界及符号链接。Markdown 本地链接和 JSON 的 dependencies、file 引用递归纳入复核。证据的 `source` 使用 HTTP(S) URL 或本地路径。本地来源（含 UTF-8 HTML）绑定文件摘要，缺失或格式不支持时阻断。远程链接只校验结构。文件删除、替换、清单变化或研究角色状态、ID、产物变化均使复核失效。JSON 必须有效、非空且无重复键或非有限数，Python 模型须能解析，CSV 必须有表头与一致列数。run.json 的运行时间戳和交付输出不纳入依赖。保留名称 delivery-result.json 不得作为输入。验收输出只写 stdout，重定向到该名称可重复运行。

不同 reviewer ID 不能证明真正独立思考；文件存在不能证明反证充分；证据格式合格不能证明来源真实或解读正确。研究类型、适用范围、关键声明完整性、缺口是否真的客观、复核论证质量仍需 AI 或人工判断。

## 命令

```sh
python3 plugins/berkshire-team/skills/berkshire-team/scripts/delivery_gate.py --run /path/to/run
python3 plugins/berkshire-team/skills/berkshire-team/scripts/delivery_gate.py --run /path/to/run --json
```

结构化输出含 status、exit_code、evidence_gate 原始结果、issues（check/artifact/reason/repair/severity）、dependencies。退出码 0=完整、2=有限、1=阻断；命令行参数用法错误为 argparse 的 2（无交付结果 JSON）。

估值范围由 `valuation.required` 声明。正文补充检查识别紧跟估值标签的金额，包括跨行和表格写法。其他表述是否构成估值结论仍需复核。依赖闭包依靠结构化清单及本地引用，研究者和复核者须登记完整的模型运行依赖，包括动态文件访问。复核或验收期间不得并发编辑产物。

入口脚本：[delivery_gate.py](../scripts/delivery_gate.py)；复核登记：[research_run.py](../scripts/research_run.py)；证据审计：[evidence_gate.py](../scripts/evidence_gate.py)。
