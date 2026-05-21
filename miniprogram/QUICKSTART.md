# 快速启动指南

## 🚀 5分钟快速开始

### 第一步：准备图标文件（必需）

TabBar需要图标才能正常显示。请选择以下任一方式：

#### 方式A：使用纯色方块（最快）

在 `miniprogram/images/` 目录下创建4个81x81的PNG图片：
- monitor.png（灰色 #8a8a8a）
- monitor-active.png（蓝色 #00d4ff）
- history.png（灰色 #8a8a8a）
- history-active.png（蓝色 #00d4ff）

#### 方式B：使用ImageMagick命令

```bash
cd /home/gao/pro/miniprogram/images
convert -size 81x81 xc:'#8a8a8a' monitor.png
convert -size 81x81 xc:'#00d4ff' monitor-active.png
convert -size 81x81 xc:'#8a8a8a' history.png
convert -size 81x81 xc:'#00d4ff' history-active.png
```

#### 方式C：下载专业图标

从 [iconfont.cn](https://www.iconfont.cn/) 下载合适的图标。

### 第二步：配置后端地址

编辑 `miniprogram/app.js`，修改第6行：

```javascript
baseUrl: 'https://app.moutai519.com.cn  // 改为您的实际后端地址
```

**测试阶段可以使用本地地址**：
```javascript
baseUrl: 'http://localhost:4000'  // 本地测试
```

### 第三步：导入微信开发者工具

1. 下载并安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开工具，选择"导入项目"
3. 项目目录选择：`/home/gao/pro/miniprogram`
4. AppID填写：使用测试号或留空
5. 点击"导入"

### 第四步：启动后端服务

在项目根目录 `/home/gao/pro` 执行：

```bash
# 方式A：直接运行
python app.py

# 方式B：使用gunicorn（推荐）
gunicorn app:app --bind 0.0.0.0:4000
```

### 第五步：测试运行

1. 在微信开发者工具中点击"编译"
2. 查看模拟器中的小程序效果
3. 测试各项功能：
   - 切换标签页（LOF/QDII/ETF/期权）
   - 搜索基金
   - 查看历史数据
   - 下拉刷新

## ⚠️ 常见问题

### Q1: TabBar不显示图标
**原因**: images目录缺少图标文件
**解决**: 按照第一步准备图标文件

### Q2: 网络请求失败
**原因**: 
- 后端未启动
- baseUrl配置错误
- 域名未在微信公众平台配置

**解决**:
- 确保后端服务正常运行
- 检查app.js中的baseUrl配置
- 开发阶段在开发者工具中勾选"不校验合法域名"

### Q3: 数据加载失败
**原因**: 后端API返回格式不匹配
**解决**: 检查后端API是否正常返回数据

### Q4: 图表不显示
**原因**: Canvas初始化问题
**解决**: 确保在onReady生命周期中初始化图表

## 📱 真机调试

1. 在微信开发者工具中点击"真机调试"
2. 使用微信扫描二维码
3. 在手机上测试小程序功能

## 🌐 正式发布

### 1. 配置正式域名

在微信公众平台配置服务器域名：
- 登录 [微信公众平台](https://mp.weixin.qq.com/)
- 开发 → 开发管理 → 开发设置
- 配置request合法域名

### 2. 上传代码

在微信开发者工具中：
- 点击"上传"
- 填写版本号和项目备注
- 提交审核

### 3. 提交审核

在微信公众平台：
- 管理 → 版本管理
- 提交审核
- 等待审核通过

### 4. 发布上线

审核通过后：
- 点击"发布"
- 小程序正式上线

## 📞 技术支持

如遇问题，请查看：
- `README.md` - 完整文档
- `images/README.md` - 图标说明
- 微信开发者工具控制台 - 查看错误日志

## ✅ 检查清单

开始前请确认：
- [ ] 已准备TabBar图标文件
- [ ] 已配置后端baseUrl
- [ ] 已安装微信开发者工具
- [ ] 后端服务正常运行
- [ ] 后端API可正常访问

全部完成后，即可开始测试！
