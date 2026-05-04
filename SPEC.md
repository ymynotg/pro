# LOF/QDII/ETF/期权 套利系统规格说明

## 1. 项目概述

- **项目名称**: 跨境套利系统
- **项目类型**: BS架构 Web应用
- **核心功能**: LOF、QDII、ETF、期权等金融产品的套利机会分析与监控
- **目标用户**: 量化交易员、机构投资者
- **技术栈**: Flask + HTML/CSS/JS

## 2. 项目结构

```
/home/gao/pro/
├── index.html          # 前端页面
├── app.py              # Flask后端服务
├── SPEC.md             # 规格文档
├── lof_config.json     # LOF基金配置文件
├── qdii_config.json    # QDII基金配置文件
├── config/
│   ├── logging.conf          # 日志配置
│   ├── szse_lof_config.json  # 深市LOF配置文件(285只)
│   └── sse_lof_config.json   # 沪市LOF配置文件(469只)
├── logs/               # 日志目录
│   ├── fund_fetcher.log
│   ├── fetch_szse_lof.log    # 深市LOF获取日志
│   └── fetch_sse_lof.log     # 沪市LOF获取日志
├── backups/            # 配置备份目录
└── scripts/
    ├── fetch_lof_shanghai.py    # LOF数据获取脚本(沪市)
    ├── update_lof_shanghai.py    # LOF数据更新脚本(沪市)
    ├── fetch_lof_szse.py         # LOF数据获取脚本(深市)-旧版
    ├── update_lof_szse.py        # LOF数据更新脚本(深市)
    ├── fetch_szse_lof.py         # 深市LOF数据获取脚本(API版)
    ├── fetch_excel_lof.py        # LOF数据生成脚本(Excel版，支持深市/沪市)
    ├── fetch_sse_lof.py          # 沪市LOF数据获取脚本(东方财富API版)
    ├── merge_lof_config.py       # LOF配置合并脚本
    ├── fetch_qdii.py             # QDII数据获取脚本
    └── update_qdii.py            # QDII数据更新脚本
```

## 3. 当前功能

### 3.1 前端功能
- 4个标签页：LOF | QDII | ETF | 期权
- 暖色调深色主题界面
- 数据表格展示（代码、名称、价格、涨跌幅、溢价率等）
- 搜索筛选功能
- 刷新按钮
- 响应式布局

### 3.2 后端功能
- Flask Web服务（端口4000）
- RESTful API接口
- 日志管理（支持级别配置）

### 3.3 数据获取脚本
- 多数据源fallback机制
- 日志记录（记录每次调用的接口来源）
- 配置文件备份

## 4. 数据源情况

| 数据源 | 状态 | 说明 |
|--------|------|------|
| akshare.fund_lof_spot_em() | ❌ 网络不通 | 备用 |
| eastmoney rankhandler POST | ✅ 可用 | 获取5xx上交所LOF，95只 |
| eastmoney searchapi | ✅ 可用 | 获取1xx深交所LOF，94只 |
| 深交所 szse.cn | ❌ 网络不通 | 实际应有285只深市LOF |
| fallback 备用数据 | ✅ 可用 | 20只基础LOF |
| eastmoney/rankhandler (ft=qdii) | ✅ 可用 | 获取345只QDII基金 |
| 用户提供的QDII_LOF列表 | ✅ 手动 | 117只QDII-LOF |

**当前LOF总数**：约189只（深交所94只 + 上交所95只）
**实际深市LOF**：20260423:深交所官网公布285只；官网API接口调用也是285只，但写入配置文件中只有10个，原因是深交所API对IP/请求频率有限制，返回缓存的第一页（pageno=1）。
**实际深市LOF**：20260423:上交所官网公布119只；
**当前QDII总数**：446只（QDII 329只 + QDII_LOF 117只）

### 深市LOF脚本
**API版 (fetch_szse_lof.py)**
- **数据源**: 深圳证券交易所 szse.cn（备用：东方财富searchapi）
- **配置文件**: config/szse_lof_config.json
- **字段**: 序号、代码、名称、管理人、类型、更新时间
- **特性**: 追加写入，代码存在不追加
- **日志**: logs/fetch_szse_lof.log
- **说明**: API版因深交所分页失效，仅获取10条，实际使用Excel版补充

**Excel版 (fetch_szse_lof_excel.py)**
- **数据源**: input/szse_lof.xlsx（深交所官网导出）
- **配置文件**: config/szse_lof_config.json
- **字段**: 序号、代码、名称、管理人、类型、拟合指数、更新时间
- **特性**: 追加写入，代码存在不追加
- **日志**: logs/fetch_szse_lof_excel.log

### 5.3 QDII_LOF类型说明
- **问题**：东方财富API无法准确区分QDII和QDII_LOF
- **解决方案**：使用用户提供的117只QDII-LOF列表手动更新
- **说明**：QDII_LOF为交易型开放式基金，可在场内交易；普通QDII为场外基金

## 5. 已知不足

### 5.1 LOF数据不完整
- **问题**：只获取名称中包含"LOF"的基金
- **遗漏**：指数LOF（如501050华夏上证50AH优选指数A）名称不含LOF但确实是LOF
- **原因**：东方财富API返回的指数LOF名称格式为"XX指数A"，不包含"LOF"字样

### 5.2 5xx代码识别问题
- **问题**：5xx开头的不一定都是LOF
- **实际情况**：
  - 501046: 财通多策略福鑫定开混合 → ❌ 不是LOF，是混合基金
  - 501050: 华夏上证50AH优选指数A → ✅ 是LOF（指数LOF）
  - 501090: 华宝中证消费龙头ETF联接A → ❌ 不是LOF，是ETF联接

### 5.3 其他标签页
- QDII、ETF、期权标签页目前仅有模拟数据
- 需要实现真实数据接口

### 5.4 akshare接口
- 当前环境网络不通，无法使用
- 等待网络恢复后可正常使用

## 6. 运行说明

### 启动后端服务
```bash
cd /home/gao/pro
python3 app.py
# 访问 http://localhost:4000
```

### 运行数据获取脚本
```bash
cd /home/gao/pro/scripts

# 初始化获取（沪市LOF）
python3 fetch_lof_shanghai.py

# 增量更新（带备份）
python3 update_lof_shanghai.py

# 获取深市LOF（API版）
python3 fetch_szse_lof.py
# 配置文件: config/szse_lof_config.json
# 日志: logs/fetch_szse_lof.log
# 说明: API版因深交所分页失效，仅获取10条

# 获取深市LOF（Excel版）- 推荐使用
# 1. 从深交所官网导出LOF列表到 input/szse_lof.xlsx
# 2. 运行脚本
#

# 获取沪市LOF（API版）

#项目	数量
#Excel配置	119只
#东方财富配置	469只
#共同基金	118只
#仅在Excel中	1只：501023 港中小企LOF
#仅在东方财富中	351只
#仅在Excel中 (1只):

#分析：东方财富配置包含大量普通混合基金、债券基金等（351只），这些在上交所官网导出文件中未显示为LOF。

#可能原因：
#东方财富API未严格过滤LOF标识，包含了名称含"LOF"但实际不是交易型开放式基金的产品
#上交所官网导出的数据更精确（119只）
#————————————————————————————————————————————————————————————————————
python3 fetch_excel_lof.py szse
# 输入: input/szse_lof.xlsx
# 输出: config/szse_lof_config.json
# 日志: logs/fetch_excel_lof.log
# 字段: 序号、代码、名称、管理人、类型、拟合指数、更新时间

# 获取沪市LOF（Excel版）- 推荐使用
# 1. 从上交所官网导出LOF列表到 input/sse_lof.xlsx
# 2. 运行脚本
python3 fetch_excel_lof.py sse
# 输入: input/sse_lof.xlsx
# 输出: config/sse_lof_config.json
# 日志: logs/fetch_excel_lof.log

# 处理全部
python3 fetch_excel_lof.py all
# 同时处理深市沪市LOF

# 合并LOF配置
python3 merge_lof_config.py
# 读取 szse_lof_config.json 和 sse_lof_config.json
# 合并生成 lof_config.json (404只)
# 备份原文件到 backups/
```

### 生成历史数据
```bash
cd /home/gao/pro/scripts

# 全量生成（重新生成所有历史数据，LOF和QDII均365天）
python3 generate_fund_history.py
# 输出: fund_history/{code}.json
# 日志: logs/generate_history.log

# 增量更新（仅更新最新一天的数据，保留历史）
python3 generate_fund_history.py --incremental
# 适用于每日定时更新

# 自定义天数全量生成
python3 generate_fund_history.py --days 100
# 默认365天

# 生成单只基金历史数据
python3 generate_fund_history.py <基金代码> [天数]
# 示例: python3 generate_fund_history.py 160105 365
```

**历史数据规则**:
- LOF和QDII统一使用365天历史数据
- 全量生成: 重新生成并替换所有历史数据文件
- 增量更新: 只追加最新一天数据，保留原有历史
- 数据来源: 腾讯K线接口(价格) + 天天基金(净值/估值)
```

### 日志配置
编辑 `config/logging.conf`:
```ini
[log]
level = DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 7. 待完善事项

- [ ] 补充指数LOF识别逻辑（名称含"指数...A"的5xx基金）
- [ ] 深市LOF补充至285只（当前仅94只）
- [x] 实现QDII数据接口（345只）
- [ ] 实现ETF数据接口
- [ ] 实现期权数据接口
- [ ] 优化LOF/非LOF基金识别算法
- [ ] akshare网络恢复后验证功能

## 8. UI/UX 规格

### 色彩系统（暖色调）
- 主色: #2d2416 (深棕)
- 次色: #3d3020 (暖棕)
- 强调色: #d4a574 (暖金)
- 上涨: #7cb342 (暖绿)
- 下跌: #ef5350 (暖红)

### 字体
- 标题: "Orbitron"
- 正文: "Source Han Sans CN"
- 数据: "JetBrains Mono"

## 9. 验收标准

### 视觉
- [x] 暖色主题正确渲染
- [x] 4个标签页可切换
- [x] 价格涨跌颜色正确

### 功能
- [x] 标签页正常切换
- [x] 数据表格渲染
- [x] 日志正常记录
- [x] 配置文件备份

## 10. LOF实时价格获取

### 10.1 东方财富K线接口（当前价）

**用途**: 获取LOF基金二级市场实时交易价格

**URL**:
```
https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param={market}{code},day,,,2,qfq
```

**参数说明**:
- `{market}`: 市场前缀，`sz`（深市，以1开头）或 `sh`（沪市，以5开头）
- `{code}`: 基金代码，如 `160105`

**示例URL**:
```
https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param=sz160105,day,,,2,qfq
```

**返回值结构**:
```json
kline_day = {
  "data": {
    "sz160105": {
      "qt": {
        "sz160105": ["51","南方积极配置LOF","160105","1.234","1.221","1.227","140",...],
        "market": [...]
      }
    }
  }
}
```

**qt数据解析**:
```python
qt = data['data'][f'{market}{code}']['qt'][f'{market}{code}']
price = qt[3]  # 当前价
```

**qt字段索引**:
| 索引 | 字段 | 示例值 | 说明 |
|------|------|--------|------|
| 0 | 状态 | "51" | 市场状态 |
| 1 | 名称 | "南方积极配置LOF" | 基金名称 |
| 2 | 代码 | "160105" | 基金代码 |
| 3 | **当前价** | "1.234" | **当前交易价格** |
| 4 | 昨收价 | "1.221" | 昨日收盘价 |
| 5 | 开盘价 | "1.227" | 当天开盘价 |
| 6 | 成交量 | "140" | 成交量（手） |

### 10.2 天天基金接口（估值/净值）

**用途**: 获取LOF基金估算净值和最新净值

**URL**:
```
https://fundgz.1234567.com.cn/js/{code}.js
```

**参数说明**:
- `{code}`: 基金代码，如 `160105`

**示例URL**:
```
https://fundgz.1234567.com.cn/js/160105.js
```

**返回值**:
```json
jsonpgz({
  "fundcode":"160105",
  "name":"南方积极配置混合(LOF)",
  "jzrq":"2026-04-24",
  "dwjz":"1.2318",
  "gsz":"1.2392",
  "gszzl":"0.60",
  "gztime":"2026-04-27 15:00"
});
```

**字段说明**:
| 字段 | 说明 | 示例值 |
|------|------|--------|
| fundcode | 基金代码 | "160105" |
| name | 基金名称 | "南方积极配置混合(LOF)" |
| jzrq | 净值日期 | "2026-04-24" |
| dwjz | 单位净值 | "1.2318" |
| gsz | 估算价格/估值 | "1.2392" |
| gszzl | 估算涨跌幅(%) | "0.60" |
| gztime | 更新时间 | "2026-04-27 15:00" |

**注意**: 部分基金（如160125）估值接口可能返回空数据 `jsonpgz();`

## 11. 前端自动刷新配置

### 11.1 配置项说明

配置文件: `config/logging.conf`

```ini
[refresh]
trading_interval = 900000        # 交易时间刷新间隔(毫秒), 默认15分钟
non_trading_interval = 0         # 非交易时间刷新间隔(毫秒), 0表示不刷新
```

**参数说明**:
| 参数 | 说明 | 单位 | 默认值 |
|------|------|------|--------|
| trading_interval | 交易时间自动刷新间隔 | 毫秒 | 900000 (15分钟) |
| non_trading_interval | 非交易时间自动刷新间隔 | 毫秒 | 0 (不刷新) |

**交易时间判断**:
- 周六、周日: 不刷新
- 工作日 9:30 - 15:05: 使用 trading_interval
- 其他时间: 使用 non_trading_interval

### 11.2 获取配置API

**URL**: `/api/config`

**返回值**:
```json
{
  "success": true,
  "refresh": {
    "trading_interval": 900000,
    "non_trading_interval": 0
  }
}
```

### 11.3 自动刷新机制

- 页面加载时自动从 `/api/config` 获取刷新配置
- 根据当前时间判断是否在交易时间内
- 交易时间内按 trading_interval 自动刷新
- 非交易时间内按 non_trading_interval 刷新 (0 表示不刷新)
- 点击"刷新数据"按钮可手动强制刷新

## 12. QDII 基金申购/赎回状态

### 12.1 数据获取

从天天基金详情页获取状态信息：
- URL: `https://fund.eastmoney.com/pingzhongdata/{code}.js`
- 字段: `fund_SgState` (申购状态), `fund_ShState` (赎回状态)

### 12.2 状态说明

| 状态值 | 显示 | 说明 |
|--------|------|------|
| 1 | 开放 | 正常申购/赎回 |
| 2 | 暂停 | 暂停申购/赎回 |
| 3 | 限大额 | 限制大额申购 |
| 其他 | - | 未知状态 |

### 12.3 响应字段

QDII API 响应新增字段：
```json
{
  "code": "000041",
  "name": "华夏全球股票(QDII)",
  "price": "1.4604",
  "change": "-0.05",
  "nav": "1.4611",
  "valuation": "1.4604",
  "premium": "-0.05",
  "subscribe_status": "开放",
  "redeem_status": "开放"
}
```
##问题记录：
#1.历史记录中的涨跌幅数据一致。----暂时没有获得历史涨跌幅的接口，只能自己计算，先不改。
#部分代码净值为0：比如-160125？时间排序问题，已解决。


#2.QDII的实时数据基本都有问题。
**注意**: 部分基金可能无法获取状态信息，此时显示 "-"