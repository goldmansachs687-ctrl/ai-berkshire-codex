# 长桥：已授权市场数据接入

用户选择整合长桥后，优先复用当前会话已连接的 Longbridge MCP。无需再启动本地服务器、申请密钥或安装 Python SDK。本集成提供真实工具路由和报表规范化脚本；连接器服务由长桥提供，不随本包复制。连接器不可用时记录原因，回退到已有公开数据/SEC路径，不能称已经取到数据。

## 证券和默认调用

默认美股，符号使用 `AAPL.US`、`MSFT.US`、`GOOGL.US`；先确认公司和类别股。其他市场只有用户明确要求时使用，港股使用 `700.HK` 而非 `00700.HK`。从当前工具清单发现 longbridge 前缀下的实际工具，以下为已验证的工具后缀，不构造不存在的接口。

| 研究需要 | 工具与参数 | 使用边界 |
| --- | --- | --- |
| 主体、业务概况 | `company(symbol)` | 历史仍读 Wiki 正文；当前职务和控制权按需补官方。账户地区可能改变返回字段 |
| 股价与证券身份 | `quote(symbols)`、`static_info(symbols)` | 保留时间戳、交易所币种、股数类型；普通/盘前/盘后价格分别列，不混用 |
| 十年年度财务 | `financial_report(symbol, kind="ALL", report_type="af", periods=10)` | 明确传 kind，避免账户特定默认接口；逐指标检查实际期间数，不能因请求10就宣称10年齐全 |
| 单张报表/季度 | `financial_report(...kind="IS"/"BS"/"CF", report_type="qf", periods=...)` 或 `financial_statement(symbol, kind, report)` | af年度、qf季度分开；financial_statement无 periods 参数，不发明参数；CF逐项确认单季/累计 |
| 原始申报入口 | `filings(symbol)` | 返回标题/链接不等于已读正文；用现有网页/PDF工具打开，长期原件可继续用 SEC |
| 机构股东 | `shareholder_top` / `shareholder` | 报告期、申报日和持股日期分开；机构排名不是投票控制权 |
| 新闻/外部观点 | `news`、`news_search` 后按需 `news_detail` | 摘要和全文分开，保留原始出处；同一转载不构成独立来源 |
| 最后参考市场预期 | `institution_rating` 及其 detail/history | 是评级数量/一致目标价，不是逐家投行的完整研报；在独立估值完成后参考 |

不要因为有长桥入口读取用户资金、账户余额、持仓、订单、流水，或添加预警/自选/发帖；当前公司研究集成只使用市场及公司公开数据。用户以后另行明确请求时再按任务授权处理。

## 保存与规范化

工具返回先保存原始 JSON（可保存整个 MCP result，也可保存解析后的 payload）。公司身份来自请求和 company/static_info，financial_report 本身可能不带 symbol，因此不要混合不同请求的结果。

```bash
python3 <skill>/scripts/longbridge_data.py normalize \
  --kind financial-report --symbol AAPL.US --report-type af \
  --retrieved-at <实际ISO8601带时区访问时间> \
  --input <输出目录>/longbridge-financial-raw.json \
  --output <输出目录>/longbridge-financial-normalized.json
```

`--kind quote` 可规范化 quote 结果。脚本只读取已保存结果、不联网、不调用私有账户接口。输出保留原字段、数值字符串、财年、期间、fp_end和JSON定位；取得不等于核验，状态固定为 FETCHED_UNVERIFIED。空值不转成零，报错/意外形状/期间不符不冒充成功。原始金额不自动缩放；百分比数值和yoy单位不能套用其他工具的约定。

规范化不是证据表的自动PASS：核对期间、单位、会计口径及公告日期后再选入 evidence.json。所有长桥接口同属一个来源路径，不把 company/financial_report/financial_statement 算作独立双源。publication_date 未提供时保留缺失，今天的快照不可回填历史时点；fp_end 是期间结束，不是公告日。十年数据不保证二十年原件或完整附注。

## 现有研究顺序

公司信息：Wiki背景/历史 + 长桥基础财务与行情 + 必要官方补证。
长期财务：长桥多期数据先搭表，再查原始披露、会计重列及不可比项。
独立估值：先由本团队完成，随后才读取长桥一致目标价作为外部观点。
正文沿用用户六部分结构，详细取数记录与差异放附件。插件更新和能力验证不恢复暂停的谷歌研究。
