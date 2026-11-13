# From reading to research / 书里的原则怎么用进研报

[English](#english) · [简体中文](#简体中文) · [Back to project / 返回项目](../README.md) · [American Water blind test / 美国水务盲评](examples/american-water-blind-test.md)

## English

The reading record covers selected passages. Each example uses original teaching inputs and shows how a rule can change a research question or calculation.

### The Intelligent Investor

Benjamin Graham, revised edition with Jason Zweig’s commentary. The reading covered selections from Chapter 8 (PDF pp. 202–205 and 216–217, printed pp. 188–191 and 202–203) and the opening of Chapter 20 (PDF pp. 526–529, printed pp. 512–515). The record distinguishes Graham’s text from Zweig’s commentary. [HarperCollins](https://www.harpercollins.com/products/the-intelligent-investor-rev-ed-benjamin-graham)

**G01. Separate changes in price from changes in value.** Check what changed in the business before interpreting a price decline as a wider margin of safety. [Plugin rule](../plugins/berkshire-team/skills/berkshire-team/references/learned-principles.md#g01价格变化与价值变化分别判断)

**Recalculate.** The price falls from $100 to $80 per share. With an unchanged conservative value of $100, the discount to value is `(100 − 80) / 100 = 20%`. If weaker cash flow lowers the estimate to $70, the same calculation gives `(70 − 80) / 70 ≈ −14.29%`, so the shares trade at a premium to the revised estimate.

### Valuation

Tim Koller, Marc Goedhart and David Wessels, eighth edition (2025). The initial reading covered the opening of Chapter 3 (PDF pp. 80–85), with the formula checked on p. 85. A later reading extended the reviewed selections to PDF pp. 80–91 and 114–115. These are page numbers from the PDF used for reading. [Wiley-VCH](https://www.wiley-vch.de/en/areas-interest/finance-economics-law/valuation-978-1-394-27941-8) · [McKinsey book overview](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/valuation-measuring-and-managing-the-value-of-companies)

**V01. Connect growth to returns on new capital and reinvestment.** In a stable-growth case with positive returns, estimate the share of after-tax operating profit (NOPAT) needed for reinvestment as growth divided by the return on new invested capital. [Plugin rule](../plugins/berkshire-team/skills/berkshire-team/references/learned-principles.md#v01增长必须和新增资本回报再投资共同建模)

**Recalculate.** Assume next-year NOPAT of $100 million, perpetual growth of 5% and a 10% discount rate. At a 20% return on new capital, reinvestment is `100 × 5% / 20% = 25`, leaving $75 million of free cash flow to the firm (FCFF). At a 10% return, reinvestment is `100 × 5% / 10% = 50`, leaving $50 million. Discounting the growing cash flows gives enterprise values of `75 / (10% − 5%) = 1,500` and `50 / (10% − 5%) = 1,000`, both in USD millions. The same growth rate can require very different cash outlays.

### Financial Shenanigans

Howard M. Schilit, Jeremy Perler and Yoni Engelhart, fourth edition (2018). The reading covered revenue recognition in Chapter 3 (PDF pp. 51–54, printed pp. 31–34) and cash flow selections from Chapters 10 and 11 (PDF pp. 171–174, 179–182 and 188–190, printed pp. 151–154, 159–162 and 168–170). [McGraw Hill](https://www.mheducation.com/highered/mhp/product/financial-shenanigans-fourth-edition.html)

**F01. Check when revenue was earned.** Trace performance obligations, customer acceptance and the reporting cutoff. [Plugin rule](../plugins/berkshire-team/skills/berkshire-team/references/learned-principles.md#f01收入增长须追问履约验收与交易实质)

**Recalculate.** A $40 million contract has one performance obligation. The facts support recognition at substantive customer acceptance, which occurs in January. This contract contributes $0 to December revenue. If December revenue of $200 million included the full contract, the illustrative adjustment is `200 − 40 = 160` million.

**F02. Check what drove operating cash flow.** Trace receivables sales, financing and spending classifications. An analytical adjustment should isolate the effect supported by the evidence. [Plugin rule](../plugins/berkshire-team/skills/berkshire-team/references/learned-principles.md#f02经营现金流也要核实质量)

**Recalculate.** Reported operating cash flow is $160 million. Assume the records show that it includes $25 million collected early through a receivables sale, with no overlapping adjustment. Removing that timing benefit gives `160 − 25 = 135` million. The result is a normalized comparison for this scenario. The reported figure remains $160 million.

### American Water blind test

The American Water Works FY2024 teaching case used a related principle card to test whether agents traced payments and adjusted payables only once. Two of two answers with the card, versus zero of two without it, showed the implied $22 million closing payable against the $24 million reported in the exercise. All four spotted the discrepancy. These observations apply to the four answers in this exercise. [Full case and grading](examples/american-water-blind-test.md#english)

## 简体中文

阅读记录只覆盖选段。每个例子使用原创教学数据，展示插件规则会怎样改变研究问题或计算结果。

### 聪明的投资者

本杰明·格雷厄姆修订版，附杰森·兹威格评注。阅读覆盖第 8 章选段（PDF 第 202–205、216–217 页，印刷第 188–191、202–203 页）和第 20 章开头（PDF 第 526–529 页，印刷第 512–515 页）。记录区分格雷厄姆正文与兹威格评注。[HarperCollins](https://www.harpercollins.com/products/the-intelligent-investor-rev-ed-benjamin-graham)

**G01。分别判断价格变化和价值变化。** 股价下跌后先核对经营事实，再判断安全边际是否扩大。[插件规则](../plugins/berkshire-team/skills/berkshire-team/references/learned-principles.md#g01价格变化与价值变化分别判断)

**复算。** 股价从每股 100 美元跌至 80 美元。若保守价值仍为 100 美元，折价为 `(100 − 80) / 100 = 20%`。若现金流走弱使估值降至 70 美元，同一算式得到 `(70 − 80) / 70 ≈ −14.29%`，意味着 80 美元的股价高于调整后的估值。

### 估值

蒂姆·科勒、马克·戈德哈特和戴维·韦塞尔斯，第八版（2025）。首次阅读第 3 章开头（PDF 第 80–85 页），并核对第 85 页公式。后续核读扩大到 PDF 第 80–91、114–115 页。这里采用阅读时所用 PDF 的页码。[Wiley-VCH](https://www.wiley-vch.de/en/areas-interest/finance-economics-law/valuation-978-1-394-27941-8) · [麦肯锡图书介绍](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/valuation-measuring-and-managing-the-value-of-companies)

**V01。把增长、新增资本回报和再投资放在一起。** 在稳定增长且新增资本回报为正的情景下，用增长率除以新增资本回报率，估算税后经营利润（NOPAT）中需要用于再投资的比例。[插件规则](../plugins/berkshire-team/skills/berkshire-team/references/learned-principles.md#v01增长必须和新增资本回报再投资共同建模)

**复算。** 假设下一年税后经营利润为 1 亿美元，永续增长率为 5%，折现率为 10%。新增资本回报率为 20% 时，再投资为 `100 × 5% / 20% = 25`，企业自由现金流（FCFF）为 7500 万美元。回报率为 10% 时，再投资为 `100 × 5% / 10% = 50`，自由现金流为 5000 万美元。把持续增长的现金流折现，企业价值分别为 `75 / (10% − 5%) = 1,500` 和 `50 / (10% − 5%) = 1,000`，单位均为百万美元。增长率一样，所需现金投入可以相差很大。

### 财务诡计

霍华德·施利特、杰里米·珀勒和约尼·恩格尔哈特，第四版（2018）。阅读覆盖第 3 章收入确认选段（PDF 第 51–54 页，印刷第 31–34 页），以及第 10、11 章现金流选段（PDF 第 171–174、179–182、188–190 页，印刷第 151–154、159–162、168–170 页）。[McGraw Hill](https://www.mheducation.com/highered/mhp/product/financial-shenanigans-fourth-edition.html)

**F01。核实收入应在哪一期确认。** 检查履约义务、客户验收及报告期截止日。[插件规则](../plugins/berkshire-team/skills/berkshire-team/references/learned-principles.md#f01收入增长须追问履约验收与交易实质)

**复算。** 一份 4000 万美元的合同只有一项履约义务。事实支持在客户实质验收时确认收入，验收发生在次年 1 月。这份合同对 12 月的收入贡献为零。如果原列报的 2 亿美元 12 月收入包含整份合同，示例调整为 `200 − 40 = 160`，单位为百万美元。

**F02。查明经营现金流改善的来源。** 追踪应收出售、融资及支出分类。分析性调整应单列证据能够支持的影响。[插件规则](../plugins/berkshire-team/skills/berkshire-team/references/learned-principles.md#f02经营现金流也要核实质量)

**复算。** 列报的经营现金流为 1.6 亿美元。假设记录显示，其中有 2500 万美元通过应收出售提前收到，且没有其他调整重复覆盖这笔钱。剔除提前回款的影响后，`160 − 25 = 135` 百万美元，作为该情景下的可比口径。列报金额仍为 1.6 亿美元。

### 美国水务盲评

美国水务 FY2024 教学案例使用一张相关原则卡，检验答题者能否追踪付款并只调整一次应付账款。有卡组 2/2 写出了隐含期末应付款 2200 万美元与题面所列 2400 万美元的对照，无卡组为 0/2。四份答卷都发现了差额。这些结果的观察范围为本次练习的四份答卷。[完整案例和评分](examples/american-water-blind-test.md#简体中文)
