# VSCode微信小程序插件使用指南

## 🔍 问题诊断

您当前的情况：
- ✅ VSCode已打开项目
- ✅ 可以看到小程序项目文件
- ❌ 没有看到小程序开发者工具界面

## 🎯 解决方案

### 方案一：使用独立的微信开发者工具（推荐）

VSCode插件功能有限，建议使用官方微信开发者工具：

#### 1. 下载微信开发者工具

访问官网下载：
```
https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html
```

选择对应系统版本：
- Windows: Windows 64位/32位
- macOS: macOS版本
- Linux: Linux版本

#### 2. 安装并打开

安装完成后，打开微信开发者工具

#### 3. 导入项目

在微信开发者工具中：
1. 点击"导入项目"或"+"按钮
2. 填写项目信息：
   - **项目目录**: `/home/gao/pro/miniprogram`
   - **AppID**: 使用测试号或留空
   - **项目名称**: 基金套利监控
3. 点击"导入"

#### 4. 开始开发

导入成功后，您可以：
- 查看项目文件结构
- 编辑代码（自动保存）
- 编译项目
- 预览效果
- 真机调试

### 方案二：配置VSCode插件

如果坚持使用VSCode，需要正确配置插件：

#### 1. 检查插件是否激活

在VSCode中：
- 按 `Ctrl+Shift+P` 打开命令面板
- 输入 "Miniprogram" 或 "小程序"
- 查看是否有相关命令

如果没有命令，说明插件未正确激活。

#### 2. 手动激活插件

尝试以下方法：

**方法A：打开小程序文件**
- 在VSCode中打开 `app.json` 文件
- 插件应该会自动识别

**方法B：使用命令激活**
- 按 `Ctrl+Shift+P`
- 输入 "Miniprogram: Open Project"
- 选择项目目录

**方法C：重新加载窗口**
- 按 `Ctrl+Shift+P`
- 输入 "Reload Window"
- 回车执行

#### 3. 查看插件输出

- 按 `Ctrl+Shift+U` 打开输出面板
- 在右侧下拉菜单选择 "Miniprogram" 或 "小程序"
- 查看插件日志信息

#### 4. 检查插件设置

在VSCode设置中搜索：
- `miniprogram`
- `miniprogram.config`

确保配置正确。

### 方案三：使用命令行工具

#### 1. 安装微信小程序CLI

```bash
npm install -g miniprogram-ci
```

#### 2. 编译项目

```bash
cd /home/gao/pro/miniprogram
miniprogram-ci build
```

## 📱 VSCode插件功能说明

### 已安装的插件

1. **crazyurus.miniprogram-vscode-extension**
   - 提供语法高亮
   - 代码提示
   - 文件模板
   - 基础编译功能

2. **overtrue.miniapp-helper**
   - 代码片段
   - API提示
   - 组件提示

### 插件提供的功能

#### 语法支持
- ✅ WXML语法高亮
- ✅ WXSS语法高亮
- ✅ JS/JSON语法支持
- ✅ 代码提示和补全

#### 代码片段
- 输入 `page` 快速创建页面
- 输入 `component` 快速创建组件
- 输入 `wxml-` 创建WXML标签

#### 命令面板命令
- `Miniprogram: Create Page` - 创建页面
- `Miniprogram: Create Component` - 创建组件
- `Miniprogram: Build` - 编译项目（如果支持）

### 插件不提供的功能

VSCode插件通常**不提供**：
- ❌ 完整的模拟器预览
- ❌ 真机调试
- ❌ 项目管理界面
- ❌ 上传发布功能

这些功能需要使用**独立的微信开发者工具**。

## 🎯 推荐工作流程

### 最佳实践：VSCode + 微信开发者工具

#### 1. 使用VSCode编辑代码
- 强大的代码编辑功能
- 丰富的插件生态
- Git集成
- 多文件编辑

#### 2. 使用微信开发者工具预览
- 实时预览
- 真机调试
- 性能分析
- 上传发布

#### 3. 同步工作
- VSCode保存文件
- 微信开发者工具自动刷新
- 实时查看效果

## 📋 操作步骤

### 步骤1：下载微信开发者工具

```bash
# Linux系统可以使用以下命令下载
wget https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html
# 或直接访问官网下载
```

### 步骤2：安装并打开

按照安装向导完成安装，然后打开工具

### 步骤3：导入项目

在微信开发者工具中：
1. 点击"导入项目"
2. 选择目录：`/home/gao/pro/miniprogram`
3. AppID留空或使用测试号
4. 点击"确定"

### 步骤4：配置项目

导入后需要：
1. 检查 `project.config.json` 配置
2. 配置AppID（如果需要）
3. 配置服务器域名（正式发布时）

### 步骤5：开始开发

现在您可以：
- 在VSCode中编辑代码
- 在微信开发者工具中预览
- 实时查看修改效果

## 🔧 常见问题

### Q1: VSCode插件没有显示小程序工具栏

**原因**: 插件功能有限，不提供完整的GUI界面

**解决**: 使用独立的微信开发者工具

### Q2: 如何在VSCode中预览小程序

**答案**: VSCode插件通常不提供预览功能，需要使用微信开发者工具

### Q3: 两个工具如何配合使用

**方法**:
1. VSCode编辑代码并保存
2. 微信开发者工具自动检测文件变化
3. 自动刷新预览

### Q4: 推荐使用哪个工具

**建议**:
- **编辑代码**: VSCode（功能更强大）
- **预览调试**: 微信开发者工具（官方支持）
- **两者配合**: 最佳开发体验

## 📚 相关资源

### 官方文档
- 微信小程序文档: https://developers.weixin.qq.com/miniprogram/dev/framework/
- 开发者工具文档: https://developers.weixin.qq.com/miniprogram/dev/devtools/devtools.html

### 项目文档
- `README.md` - 项目完整文档
- `QUICKSTART.md` - 快速开始指南
- `IDE_IMPORT_GUIDE.md` - IDE导入指南

## 🎯 总结

**VSCode插件的作用**:
- ✅ 代码编辑增强
- ✅ 语法高亮和提示
- ✅ 代码片段
- ❌ 不提供完整开发环境

**推荐方案**:
- 使用 **VSCode** 编辑代码
- 使用 **微信开发者工具** 预览调试
- 两者配合使用，获得最佳体验

**下一步**:
1. 下载并安装微信开发者工具
2. 导入项目目录：`/home/gao/pro/miniprogram`
3. 开始开发和测试

---

**创建时间**: 2026-05-21
**适用场景**: VSCode插件无法显示完整开发工具界面
