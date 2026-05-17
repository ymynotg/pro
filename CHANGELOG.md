# Changelog

## 2026-05-14: 增量更新模式改为原地更新

### 修改文件
- `scripts/generate_fund_history.py`

### 背景
原增量更新逻辑在检测到今天数据已存在时直接跳过，无法将盘中变化的净值（nav）、估值（valuation）、收盘价（price）等字段刷新为最新值。

### 修改内容
`update_fund_history()` 函数中，将数据已存在时的跳过逻辑改为原地更新：

1. **不再跳过**，而是用最新 API 数据覆盖 `old_data['history'][0]` 的字段
2. **涨跌幅重新计算**：对比前一交易日的 `price` 计算
3. **溢价率重新计算**：用最新 `price` 和 `nav` 计算
4. **新增日志**：更新完成后记录 price/nav/change/premium 的具体数值

### 变更对比

| 项目 | 原逻辑 | 新逻辑 |
|------|--------|--------|
| 当天数据已存在 | 跳过，不做任何操作 | 更新 nav/valuation/price/change/premium 字段 |
| 涨跌幅 | 不处理 | 用最新 price 对比前一天重新计算 |
| 溢价率 | 不处理 | 用最新 price 和 nav 重新计算 |
| update_time | 不更新 | 刷新为当前时间 |
| 日志 | 记录"跳过增量更新" | 记录具体更新后的字段值 |

### 相关函数
- `get_tencent_kline()` — 获取最新收盘价
- `get_historical_nav()` — 获取最新单位净值
- `get_fund_realtime()` — 获取盘中实时估值

---

# 系统问题与跟踪

## [已解决] 历史数据页面刷新按钮 spinner 图标尺寸异常

- **现象**: 点击"刷新数据"按钮后，loading 圆圈 spinner 变得很大
- **原因**: spinner 使用 `<span>` 元素，依赖 `.refresh-btn.loading .spinner` 的 `display: inline-block` 渲染。按钮未使用 flex 布局，spinner 的宽高在 inline-block 下受父元素 line-height 和 vertical-align 影响被拉伸
- **修复**: 将 `.refresh-btn` 设为 `display: inline-flex; align-items: center; gap: 6px;`，spinner 设为 `display: block; flex-shrink: 0;`，确保尺寸固定

## [已解决] generate_fund_history.py 增加代码注解和日志

- **内容**: 
  - 文件头添加了详细功能说明和用法示例
  - 每个函数添加了中文文档注释（参数、返回值、流程）
  - 关键逻辑处增加行内注释
  - 增加 INFO/DEBUG 级别日志覆盖各 API 调用环节

## [已解决] 历史数据页面增加"刷新数据"按钮

- **内容**:
  - app.py 新增 `POST /api/history/generate/<code>` 接口，调用 `generate_fund_history.py <code> --days 2000` 重新生成数据
  - history.html 右上角新增"刷新数据"按钮，点击后显示 loading 动画，完成后自动刷新页面数据

## 2026-05-12

### 1. 涨跌幅/溢价率/估溢率无着色方案

**状态**：未解决

**问题**：
- `change_percent`（场内交易涨跌幅）在值为 0 时，后端返回空字符串 `''`，前端 JS 解析为 `null`，导致 `changeClass` 为空，无着色
- 休市时段所有 `change_percent` 均为 0，整表涨跌幅列全无色
- ETF 模拟数据字段名使用 `change` 而非 `change_percent`，与前端渲染逻辑不匹配
- **根因**：休市时段 `price=0`，`premium = ((price-nav)/nav*100)` 条件 `price>0` 不成立 → `premium=0` → Python `round(0,2) if 0 else ''` 返回空字符串 → 前端 `parseFloat('')||0 = 0` → 永无颜色

**尝试过的修复（均未生效）**：
- app.py: 引入 `effective_price` 用 valuation 替代 price 计算 premium
- index.html: 涨跌幅 fallback 到 `item.change`、颜色修正、premium 背景块样式、阈值全覆盖
- history.html: 同步更新颜色样式

**说明**：当前数据页面中涨跌幅、溢价率、估溢率三列仍无着色，需进一步排查。

### 2. 溢价率/估溢率阈值配置

**状态**：已完成

**当前阈值**（数据页与历史页一致）：
- `> 5%` → high（深红）
- `> 1%` → medium（橙）
- `< -5%` → low（绿）
- `< -1%` → cyan（青）

**说明**：当前数据页面（index.html）和历史数据页面（history.html）的溢价率/估溢率着色阈值已统一。

---

### 3. 增加分类基金：封闭/定开

**状态**：待实现

**需求**：
- 区分封闭式基金和定期开放式基金，在表格中增加分类标识或单独分组展示
- 封闭/定开基金的溢价率特征与普通开放式基金不同，需区别监控

---

### 4. 现金限购申购 ETF

**状态**：待实现

**需求**：
- 支持现金限购申购的 ETF 类型
- 在 ETF 表格中增加申购限额、赎回状态等字段列
- 参考 QDII 表格的 `status-tag` 样式展示限购状态（开放/暂停/限额）
