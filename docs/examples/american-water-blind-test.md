# American Water Works FY2024 blind test / 美国水务 FY2024 盲评

[English](#english) · [简体中文](#简体中文) · [Back to project / 返回项目](../../README.md)

## English

### Setup

On November 12, 2026 (Hong Kong time), four Codex agents independently wrote a valuation memo from the same evidence. Within each of two pairs, one agent was randomly assigned an additional principle card. The common prompt asked for two years of free cash flow to the firm (FCFF), a steady-state year, and enterprise value. The prompt gave no accounting hints. The handout omitted the ledger mapping for one payment batch and contained a year-one payable discrepancy. An independent grader scored anonymized answers against a rubric fixed before dispatch. Group assignments were revealed after grading.

American Water Works’ FY2024 filing supplies the historical accounting policy. It describes expensing repairs, maintenance, and minor replacements as incurred, and capitalizing utility plant additions and replacement of retired units of property. The payment batches, payables, forecast, and enterprise values below are simulated teaching figures. [FY2024 Form 10-K, pp. 100 and 105](https://www.sec.gov/Archives/edgar/data/1410636/000141063625000022/awk-20241231.htm)

The card covered three checks. Trace payments to invoices, contracts, or ledger entries before treating them as the same outlay. When starting from accrual earnings, adjust for the payable movement once or substitute cash paid for the expense. If records fail to reconcile, quantify the discrepancy and value plausible classifications separately until the evidence resolves it.

### Blind results

| Outcome | With card | Without card |
| --- | ---: | ---: |
| Found the missing mapping | 2/2 | 2/2 |
| Found the first-year $2 million payable discrepancy | 2/2 | 2/2 |
| Showed the implied $22 million closing payable against the reported $24 million | 2/2 | 0/2 |
| Double-counted an expense in the submitted model | 0/2 | 0/2 |
| Valued the scenario where both payments had to be borne separately | 2/2 | 1/2 |
| Blind scores out of 10 | 10, 9 | 8, 7 |

Both card answers explicitly modeled Q12 as separate capital spending in the downside case. One control answer modeled the equivalent separate cash outflows while leaving the accounting classification open. Three answers led with about $9,976.2 million. One card answer led with about $8,868.3 million as its conservative conditional estimate. Estimates using the same assumptions agreed within rounding.

### Valuation bridge

Year-one opening payables of $10 million plus $80 million of accrued E62 expense less the reported $24 million closing payable imply a $66 million payment. Assigning the $68 million Q12 payment to E62 would instead yield a $22 million closing payable. The later years reconcile if the payments are linked, but matching amounts alone leave the classification unresolved.

| Scenario | FCFF in year 1 / year 2 / steady state (USD millions) | Enterprise value (USD millions) |
| --- | --- | ---: |
| Use the ledger-implied E62 cash payment and assume Q12 adds no cash outflow | 802 / 803.5 / 797.5 | 9,978.06 |
| Treat Q12 as the same operating payment and use the cash schedule | 800 / 803.5 / 797.5 | 9,976.21 |
| Treat Q12 as incremental capital spending and use the ledger for E62 | 734 / 707.5 / 707.5 | 8,868.29 |

The ledger case starts with after-tax EBIT (900 / 937.5 / 937.5), adds depreciation (550 each year) and the change in the two operating payables (+22 / −9 / 0), then subtracts verified capital spending (655 / 680 / 690) and other working capital investment (+15 / −5 / 0). The same-payment case replaces the first year's ledger-implied $66 million payment with $68 million. The separate-capital case subtracts Q12 (68 / 96 / 90) from the ledger case. With 8% discounting and zero growth, divide steady-state FCFF by 8% at the end of year two and discount it with the two explicit annual cash flows.

The $2 million first-year discrepancy changes enterprise value by **$1.85 million**. The two payment classifications differ by **$1,107.92 million**, driven mainly by whether the $90 million steady-state outflow is incremental. In this four-answer run, the card group covered that scenario more consistently. Both groups avoided double-counting. Two answers per group leave the card’s effect on future error rates uncertain. Matching Q12 to the underlying contract, invoice, payment record, and fixed-asset entry would resolve the classification. Payable postings and reversals could explain the remaining discrepancy.

## 简体中文

### 实验设计

2026 年 11 月 12 日（香港时间），四个 Codex 子智能体各自用同一份材料写估值备忘录。将四份作答分为两对，每对随机给一位答题者额外发放原则卡。共同题干要求给出前两年和稳态年度的企业自由现金流（FCFF）及企业价值。题干没有会计提示。材料省略了一笔付款的总账对应，并留了一笔首年应付差额。独立评审用派题前封存的标准给匿名答卷打分，评分后才揭晓分组。

美国水务 FY2024 年报提供历史会计政策。年报说明，修理、养护和小件更换在发生时计入费用，公用设施新增及退役资产单元的更换计入资本支出。下文的付款批次、应付余额、预测和企业价值均为教学模拟数据。[FY2024 年报，第 100、105 页](https://www.sec.gov/Archives/edgar/data/1410636/000141063625000022/awk-20241231.htm)

原则卡要求做三项检查。用发票、合同或总账分录确认两处记录是否属于同一笔支出。从应计利润出发时，只调整一次应付变动，或用实付金额替换应计费用。账款对不上时，量化差额，并在证据补齐前分别估算合理归属情景的价值。

### 盲评结果

| 项目 | 有原则卡 | 无原则卡 |
| --- | ---: | ---: |
| 发现缺失的科目对应 | 2/2 | 2/2 |
| 发现首年 200 万美元的应付差额 | 2/2 | 2/2 |
| 写出推算期末应付 2,200 万美元与账载 2,400 万美元 | 2/2 | 0/2 |
| 在实际提交的模型中重复扣款 | 0/2 | 0/2 |
| 算出需要分别承担两笔付款时的估值 | 2/2 | 1/2 |
| 盲评分（满分 10） | 10、9 | 8、7 |

两份有卡答卷都明确将 Q12 作为独立资本支出测算下行情景。一份无卡答卷测算了等价的独立现金流出，保留会计归属待核。三份答卷主报约 9,976.2 百万美元。一份有卡答卷主报约 8,868.3 百万美元，作为审慎情景。采用同一假设时，估值只差舍入。

### 估值推导

首年期初应付 1,000 万美元，加 E62 当年应计费用 8,000 万美元，减账载期末应付 2,400 万美元，隐含付款 6,600 万美元。若把 Q12 的 6,800 万美元付款归给 E62，期末应付应为 2,200 万美元。假定两者是同一笔付款，后续年份的余额能够对上，但金额吻合仍不足以确认归属。

| 情景 | 第 1 年／第 2 年／稳态 FCFF（百万美元） | 企业价值（百万美元） |
| --- | --- | ---: |
| 采用账载应付推算 E62 付款，假定 Q12 没有增量现金支出 | 802 / 803.5 / 797.5 | 9,978.06 |
| 将 Q12 视为同一笔经营付款，采用资金付款表 | 800 / 803.5 / 797.5 | 9,976.21 |
| 将 Q12 视为增量资本支出，E62 按账载应付计算 | 734 / 707.5 / 707.5 | 8,868.29 |

账载情景从税后经营利润（900 / 937.5 / 937.5）出发，加回折旧（每年 550）和两笔经营应付变动（+22 / −9 / 0），再减已核实的资本支出（655 / 680 / 690）及其他营运资本投入（+15 / −5 / 0）。同笔付款情景把首年账载隐含付款 66 换成实付 68。独立资本支出情景从账载情景另扣 Q12（68 / 96 / 90）。以 8% 折现率、零增长计算，在第 2 年末用稳态 FCFF 除以 8% 得到终值，再将终值与前两年现金流折现至期初。

首年 200 万美元的勾稽差使企业价值相差 **185 万美元**。两种付款归属使企业价值相差 **11.0792 亿美元**，主要取决于稳态每年 9,000 万美元是否为增量支出。这四份答卷里，有卡组更一致地量化了该情景，两组都避免了重复扣款。每组两份答卷，原则卡对后续错误率的影响仍待检验。补齐 Q12 对应的合同、发票、付款凭证和固定资产分录，可以确认归属。应付过账和冲销记录可用于解释剩余差额。
