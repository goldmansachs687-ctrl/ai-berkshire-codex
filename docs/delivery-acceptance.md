# 交付验收复现说明

[判定规则与数据契约](../plugins/berkshire-team/skills/berkshire-team/references/delivery-acceptance.md)是唯一规范。现有 evidence gate 和 research_run 命令保持兼容，新增契约不会自动迁移或批准旧研究。

从仓库根目录执行（Python 3.12；运行测试需要 requirements-ci.txt，交付门禁自身仅使用标准库）：

```sh
python3 -m pip install -r requirements-ci.txt
python3 scripts/check_plugins.py
python3 scripts/run_tests.py
python3 tests/make_delivery_examples.py --output /tmp/berkshire-examples
```

生成器打印四个目录：complete、limited、blocked、qualitative。目录包含固定的**虚构研究数据和虚构复核记录**；每次新建目录，不覆盖旧样例。模型可执行 `python3 <complete目录>/model.py`，输出 1000；门禁独立重算相同算式，不执行任意模型代码。

```sh
python3 plugins/berkshire-team/skills/berkshire-team/scripts/delivery_gate.py --run <complete目录>
python3 plugins/berkshire-team/skills/berkshire-team/scripts/delivery_gate.py --run <limited目录> --json
python3 plugins/berkshire-team/skills/berkshire-team/scripts/delivery_gate.py --run <blocked目录> --json
```

期望分别为 COMPLETE/0、LIMITED/2、BLOCKED/1；qualitative 是无估值模型的限定范围简报，COMPLETE/0 仅表示该简报适用流程完成。LIMITED 不是 evidence PASS。BLOCKED 样例四角色 pending、证据为空，尽管虚构复核标 complete 仍阻断。

复核后的变更：在 complete 的 report.md、evidence.json、model.py 或 inputs.json 任一文件追加换行，再运行门禁，必须 BLOCKED；即使语义相同，文件内容已变也需要重新复核。删除必要依赖同样阻断。把输出重定向到 `delivery-result.json` 后再次验收，输入不变则结果完全一致。

真实研究须先填写 delivery.json、质询记录、模型 manifest、review.md 和 review.json，实际独立复核完成后，沿用原命令：

```sh
python3 plugins/berkshire-team/skills/berkshire-team/scripts/research_run.py checkpoint \
  --run <研究目录> --role independent_review --status complete \
  --file review.md --note '填写实际复核结论与限制' --agent-id <实际复核者ID>
```

系统自动纳入模型、输入、输出及必要依赖；不能用重复 checkpoint 代替真正重审。验收本身绝不会调用 checkpoint。

CI 在 push 和 pull_request 执行相同配置检查和全套测试。包级版本分别核对，历史版本和上游版本不会被误判为必须一致。测试入口发现 skip/expected failure、空套件或真实失败均返回非零。CI 只验证配置和测试。结果可在仓库的 Actions 页面查看。
