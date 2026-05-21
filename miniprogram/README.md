# 基金套利监控微信小程序

## 项目简介

本项目是将原有的LOF/QDII基金套利监控系统转换为微信小程序版本，提供移动端访问能力。

## 技术栈

- **前端框架**: 微信小程序原生框架
- **样式**: WXSS（CSS适配）
- **图表**: Canvas 2D
- **后端**: Flask（复用原有后端）

## 项目结构

```
miniprogram/
├── app.js                 # 小程序入口文件
├── app.json               # 小程序配置文件
├── app.wxss               # 全局样式
├── sitemap.json           # 站点地图配置
│
├── pages/                 # 页面目录
│   ├── index/             # 首页（监控页面）
│   │   ├── index.js
│   │   ├── index.json
│   │   ├── index.wxml
│   │   └── index.wxss
│   └── history/           # 历史数据页面
│       ├── history.js
│       ├── history.json
│       ├── history.wxml
│       └── history.wxss
│
├── utils/                 # 工具类目录
│   ├── api.js             # API接口定义
│   ├── request.js         # 网络请求封装
│   └── util.js            # 通用工具函数
│
└── images/                # 图片资源目录
    ├── monitor.png        # 监控图标
    ├── monitor-active.png # 监控激活图标
    ├── history.png        # 历史图标
    └── history-active.png # 历史激活图标
```

## 功能特性

### 1. 首页（监控页面）
- ✅ 4个标签页切换（LOF | QDII | ETF | 期权）
- ✅ 数据列表展示（代码、名称、价格、涨跌幅、溢价率等）
- ✅ 搜索筛选功能
- ✅ QDII数据清洗功能
- ✅ 下拉刷新
- ✅ 自动刷新（可配置）
- ✅ 数据统计（总数、正溢价、负溢价）

### 2. 历史数据页面
- ✅ 基金详情展示
- ✅ 时间范围选择（7天、30天、90天、1年）
- ✅ 溢价率走势图表
- ✅ 统计信息（平均、最高、最低、波动率）
- ✅ 历史记录列表

## 配置说明

### 1. 后端API配置

在 `app.js` 中修改 `baseUrl`：

```javascript
globalData: {
  baseUrl: 'https://your-domain.com', // 替换为实际域名
  // ...
}
```

**重要提示**：
- 小程序要求使用HTTPS协议
- 需要在微信公众平台配置合法域名
- 域名需要ICP备案

### 2. 微信公众平台配置

1. 登录[微信公众平台](https://mp.weixin.qq.com/)
2. 进入"开发" -> "开发管理" -> "开发设置"
3. 配置服务器域名：
   - request合法域名：`https://your-domain.com`
4. 配置业务域名（可选）

### 3. TabBar图标配置

需要准备以下图标文件（尺寸：81x81px）：

- `images/monitor.png` - 监控图标（未选中）
- `images/monitor-active.png` - 监控图标（选中）
- `images/history.png` - 历史图标（未选中）
- `images/history-active.png` - 历史图标（选中）

## 使用说明

### 1. 导入项目

1. 下载并安装[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开微信开发者工具
3. 选择"导入项目"
4. 选择 `miniprogram` 目录
5. 填写AppID（测试可使用测试号）

### 2. 配置后端

确保原有的Flask后端正常运行：

```bash
# 启动后端服务
python app.py

# 或使用gunicorn
gunicorn app:app --bind 0.0.0.0:4000
```

### 3. 测试运行

1. 在微信开发者工具中点击"编译"
2. 查看小程序运行效果
3. 使用"真机调试"在手机上测试

## API接口说明

小程序复用原有后端API接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/lof` | GET | 获取LOF基金数据 |
| `/api/qdii` | GET | 获取QDII基金数据 |
| `/api/etf` | GET | 获取ETF基金数据 |
| `/api/option` | GET | 获取期权数据 |
| `/api/fund/<code>` | GET | 获取单只基金详情 |
| `/api/fund/batch` | POST | 批量查询基金 |
| `/api/history/<code>` | GET | 获取历史数据 |
| `/api/refresh` | POST | 刷新数据 |
| `/api/config` | GET | 获取配置信息 |
| `/api/stats` | GET | 获取统计信息 |

## 样式说明

小程序使用CSS变量系统，定义在 `app.wxss`：

```css
/* 主要颜色 */
--primary-color: #00d4ff;      /* 主色 */
--secondary-color: #ff6b6b;    /* 辅助色 */
--success-color: #4ade80;      /* 成功色 */
--danger-color: #ef4444;       /* 危险色 */

/* 背景颜色 */
--bg-primary: #0f0f1e;         /* 主背景 */
--bg-secondary: #1a1a2e;       /* 次背景 */
--bg-tertiary: #252542;        /* 三级背景 */
--bg-card: #1e1e3f;            /* 卡片背景 */

/* 文本颜色 */
--text-primary: #ffffff;       /* 主文本 */
--text-secondary: #b8b8d0;     /* 次文本 */
--text-muted: #6b6b8a;         /* 弱化文本 */
```

## 性能优化

1. **数据缓存**: 使用小程序缓存机制，减少网络请求
2. **防抖节流**: 搜索输入使用防抖，避免频繁请求
3. **按需加载**: 历史数据按时间范围加载
4. **图表优化**: Canvas绑定在页面ready后初始化

## 注意事项

1. **域名配置**: 必须使用HTTPS域名，并在微信公众平台配置
2. **数据格式**: 确保后端返回的数据格式与小程序兼容
3. **权限申请**: 部分功能可能需要用户授权
4. **版本兼容**: 注意小程序基础库版本兼容性

## 后续优化建议

1. **数据缓存**: 实现本地数据缓存，提升加载速度
2. **骨架屏**: 添加骨架屏，提升用户体验
3. **错误处理**: 完善错误处理和重试机制
4. **性能监控**: 添加性能监控和埋点
5. **推送通知**: 实现溢价率预警推送
6. **分享功能**: 添加分享到好友功能

## 开发团队

- 原系统开发：基金套利监控系统团队
- 小程序转换：华为云码道（CodeArts）代码智能体

## 版本历史

- v1.0.0 (2026-05-21): 初始版本，完成基础功能转换
