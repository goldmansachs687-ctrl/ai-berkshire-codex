# 本地AKShare与EdgarTools取证

本插件自带只读适配器`scripts/market_data.py`。它通过工作区专用环境实际调用两个库，输出JSON证据包；不是仅提供项目链接，也不是额外的MCP服务。已有可用环境先自检，不在研究中自动安装或升级依赖。

## 环境与身份

脚本入口可用Python 3.9+启动；数据运行环境要求Python 3.11+，已测试Python 3.12。它优先读取`BERKSHIRE_DATA_PYTHON`，其次读取工作区`.berkshire/data-runtime.json`的`python`，默认`.runtime/market-data/bin/python`。相对路径以`--workspace`解析，代理切换cwd时仍须传正确工作区。

```bash
python3 <skill>/scripts/market_data.py --workspace <workspace> doctor
```

READY表示包可以导入；`network_tested=false`明确未测试上游。一次成功查询也只证明该接口在该时刻可用。

新机器安装：先准备Python 3.11+，用其`-m venv <workspace>/.runtime/market-data`建环境，再用该环境的`python -m pip install -r <skill>/references/market-data-requirements.txt`安装已测试版本。完整传递依赖和实测记录保留在部署工作区；插件包不携带虚拟环境。按主机权限处理下载，勿修改系统Python。

工作区配置示例：

```json
{"schema_version":1,"python":".runtime/market-data/bin/python","edgar_identity":"你的姓名 你的完整邮箱"}
```

EdgarTools也接受用户配置的`EDGAR_IDENTITY`环境变量，优先于文件。真实身份随SEC请求发送；缺失则SEC查询返回INCOMPLETE，不使用伪造邮箱。身份放本地私有配置，限制文件权限并忽略版本提交，不写入报告、日志或插件包。缓存位于工作区`.runtime/cache/edgar`。适配器设置默认每秒3次SEC请求，仍受上游限制。

## 数据路由与命令

`--output`指向研究目录下的data文件夹；每次生成唯一子目录和bundle.json，不覆盖前次查询。所有日期为明确的ISO日期，不把示例日期当本轮截止日。

| 需求 | 命令 | 证券及边界 |
| --- | --- | --- |
| 港股历史日线 | `ak-prices --market hk --symbol 00700 --start <YYYY-MM-DD> --end <YYYY-MM-DD>` | 5位当地代码；默认不复权。市场代码不单独证明交易币种，核实证券及交易柜台 |
| 中国股票历史日线 | `ak-prices --market cn --symbol 600519 --start <日期> --end <日期>` | 6位当地代码；核实证券类别，不能将B股等自动当人民币A股 |
| 港股三表原始历史 | `ak-hk-financials --symbol 00700 --statement 利润表 --frequency 年度` | 亦支持资产负债表、现金流量表及报告期；这是当前供应商的历史数据，不是按公告日截断的历史快照 |
| SEC申报列表 | `edgar-filings --symbol AAPL --form 10-K --as-of <日期>` | 也可用CIK如320193；按公开申报日筛选；列表保留accession与原文链接 |
| SEC申报三表 | `edgar-financials --symbol AAPL --form 10-K --as-of <日期>` | 取截止日前最新匹配申报中的XBRL；列可能包含多个比较期间，不能把第一列机械当最新期间 |
| SEC特定申报正文 | `edgar-text --symbol AAPL --form 10-K --as-of <日期> --accession <实际编号>` | 必须属于指定公司、表单且在截止日前；保存filing.txt及哈希；取正文不等于已阅读 |

完整示例形态：

```bash
python3 <skill>/scripts/market_data.py --workspace <workspace> ak-prices --market hk --symbol 00700 --start <日期> --end <日期> --output <run>/data
```

SEC表单还支持10-Q、20-F、6-K、8-K及各自的/A更正表单；按精确表单匹配，10-K不会静默混入10-K/A。若需检查更正，另查`--form 10-K/A`并与原始申报比较，不假设更正一定包含全套财务。各表单的财务/XBRL内容不保证完整。研究腾讯港股时优先公司IR/港交所原始披露与AKShare辅助数据，不把00700或ADR自动映射到另一证券。已连接的Quartr和其他数据商仍按当前能力使用。

行情默认使用东方财富；`ak-prices --market hk --source sina`显式切换新浪港股来源，仍由AKShare执行。切换会在query、upstream_api、URL及origin_group中留痕，不静默改源。本轮东方财富行情连接失败，而新浪港股与东方财富港股财务接口成功；这是部署时实测，不是长期可用性保证。

## 证据流转

1. 查阅bundle.json里的status、真实日期、sources、datasets、warnings和截断状态。原始表格保留来源列名和空值，0仍为0。默认最多2000行，可用`--limit`调整，范围1–10000；截断会返回INCOMPLETE。
2. 来源包含URL、locator和底层origin_group；包级accessed_at是实际查询时刻。AKShare是访问库，不能把它当与东方财富独立的数据源。披露转引与原公告也不自动独立。
3. HK财务金额币种/数量级/会计准则未由适配器自动证明；SEC三表保留原列和标签，需要读取申报核对XBRL单位、期间与维度。历史复盘还须处理更正和当时可得性。
4. 主代理从选定行及原文建立`evidence.json` observation，填真实metric/unit/currency/period/basis、来源和具体JSON行/原文位置。做转换需记录原值和计算；初始source family若过粗，结合原公告统一血缘，不能人为改成两个来源。
5. 再运行evidence_gate和独立复核。FETCHED只表示取回数据；不等于PASS，不把行情查询当财报核验，不把证据包中的警告静默删除。

返回码0表示FETCHED或READY；2表示EMPTY、INCOMPLETE或ERROR。缺库、缺身份、模式变化、超时、空返回及上游拒绝都明确记录。单次任务最多120秒，错误保留证据包；使用已授权原始披露替代，不伪造结果或不停重试。

主要维护来源：[AKShare](https://github.com/akfamily/akshare)、[EdgarTools](https://github.com/dgunning/edgartools)、[EdgarTools SEC身份说明](https://edgartools.readthedocs.io/en/latest/resources/sec-compliance/)。两库为外部安装依赖，代码MIT许可；上游数据使用条件仍适用。
