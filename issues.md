# 问题记录

## [已修复] 历史数据页面刷新按钮 spinner 图标尺寸异常

- **现象**: 点击"刷新数据"按钮后，loading 圆圈 spinner 变得很大
- **原因**: spinner 使用 `<span>` 元素，依赖 `.refresh-btn.loading .spinner` 的 `display: inline-block` 渲染。按钮未使用 flex 布局，spinner 的宽高在 inline-block 下受父元素 line-height 和 vertical-align 影响被拉伸
- **修复**: 将 `.refresh-btn` 设为 `display: inline-flex; align-items: center; gap: 6px;`，spinner 设为 `display: block; flex-shrink: 0;`，确保尺寸固定

## [已修复] generate_fund_history.py 增加代码注解和日志

- **内容**: 
  - 文件头添加了详细功能说明和用法示例
  - 每个函数添加了中文文档注释（参数、返回值、流程）
  - 关键逻辑处增加行内注释
  - 增加 INFO/DEBUG 级别日志覆盖各 API 调用环节

## [已修复] 历史数据页面增加"刷新数据"按钮

- **内容**:
  - app.py 新增 `POST /api/history/generate/<code>` 接口，调用 `generate_fund_history.py <code> --days 2000` 重新生成数据
  - history.html 右上角新增"刷新数据"按钮，点击后显示 loading 动画，完成后自动刷新页面数据
