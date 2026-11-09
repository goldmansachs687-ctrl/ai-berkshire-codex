# 统一证据表

`evidence.json`是关键字段的明确覆盖表；Markdown抽检只查额外抄录错误。主代理单写此文件。适用字段包括价格/时间、股份类型与股本、汇率方向/时间、期间收入及各利润口径、OCF、现金与确认capex、SBC、现金债务、重要合同承诺，以及决策敏感的其他事实。没有估值的研究可移除无关价格字段，但须在scope_notes说明；不能因取不到数而删除。

格式示例仅为虚构结构，不是腾讯或任何公司的事实：

```json
{
  "schema_version": 1,
  "required_claims": ["revenue"],
  "scope_notes": "限定核验年度收入；该示例不包含估值",
  "claims": [{
    "id": "revenue", "kind": "fact", "label": "年度收入",
    "metric": "consolidated_revenue", "reported_value": 100,
    "unit": "million", "currency": "CNY", "period": "FY20XX", "basis": "IFRS",
    "observations": [{
      "value": 100, "metric": "consolidated_revenue", "unit": "million",
      "currency": "CNY", "period": "FY20XX", "basis": "IFRS",
      "source": "实际原始公告URL或本地文件", "locator": "第X页，具体行项目",
      "accessed_at": "实际读取日期", "origin_group": "同一发行人-同一期公告"
    }]
  }]
}
```

每项至多放两条规范化核验观察；更多来源保存sources.md。原始单位不同须保存原值、转换公式；最终observation的metric/unit/currency/period/basis必须一致才比较。`kind=derived`的observation另需`calculation`说明原数到结果，程序不执行字符串公式。非货币字段currency="N/A"，不要留空冒充遗忘。

使用两个平台时记录底层origin_group。新闻稿、财报、镜像及转引同一披露不独立；原始单源可验证抄录，但不能声称独立双核。只有确实需要独立来源的事实才设require_independent_sources=true；无法确认血缘不伪填不同组。可设置require_second_source=true要求两条展示路径，二者并非同一要求。

source填原文件地址，页码或锚点放locator。仅片段和UTM参数不同的同一地址不能充当第二来源；保存原始文件时可填可选source_sha256，两个相同的原文件指纹不能算独立。不同网址和分组仍需人工追溯底层披露。

模型假设设kind="assumption"并写rationale，不以伪造的观察值“验证”。假设不能替代required_claims里的历史事实。未知原数保留null并记录缺口，不能填0。

工具返回：PASS仅证明声明字段的数值与已提交证据、元数据一致；FAIL代表实质数值差异/无效输入；INCOMPLETE代表缺字段、缺来源或口径尚未统一。程序不联网、不鉴定URL真假，也不能检测代理虚报阅读，因此还必须实际读取来源并由独立复核抽查。
