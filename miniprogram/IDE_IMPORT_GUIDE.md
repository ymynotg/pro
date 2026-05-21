# 使用VSCode微信小程序插件导入项目指南

## 📦 已安装的插件

检测到您已安装以下微信小程序相关插件：
- ✅ `crazyurus.miniprogram-vscode-extension` - 微信小程序开发工具
- ✅ `overtrue.miniapp-helper` - 小程序开发助手

## 🚀 导入项目步骤

### 方法一：通过VSCode打开项目（推荐）

1. **在VSCode中打开项目目录**
   - 打开VSCode
   - 选择 `文件` → `打开文件夹`
   - 选择路径：`/home/gao/pro/miniprogram`
   - 点击"确定"

2. **插件会自动识别**
   - 打开后，微信小程序插件会自动识别项目
   - 左侧边栏会出现"小程序"图标
   - 底部状态栏会显示小程序相关信息

3. **配置AppID**
   - 点击底部状态栏的"小程序"按钮
   - 或使用命令面板（Ctrl+Shift+P）搜索"小程序"
   - 选择"设置AppID"，输入测试AppID或留空

### 方法二：通过命令面板导入

1. **打开命令面板**
   - 按 `Ctrl+Shift+P`（Windows/Linux）
   - 或 `Cmd+Shift+P`（macOS）

2. **搜索小程序命令**
   - 输入"小程序"或"miniprogram"
   - 选择"Miniprogram: Open Project"或类似命令

3. **选择项目路径**
   - 选择 `/home/gao/pro/miniprogram` 目录

### 方法三：使用微信开发者工具（独立应用）

如果VSCode插件无法满足需求，可以使用独立的微信开发者工具：

1. **下载微信开发者工具**
   - 访问：https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html
   - 选择对应系统版本下载

2. **导入项目**
   - 打开微信开发者工具
   - 选择"导入项目"
   - 项目目录：`/home/gao/pro/miniprogram`
   - AppID：使用测试号或留空
   - 项目名称：基金套利监控

## 🎯 导入后需要做的事

### 1. 准备TabBar图标（必需）

在 `miniprogram/images/` 目录下创建图标文件：

**快速方法（使用纯色方块）**：
```bash
cd /home/gao/pro/miniprogram/images

# 如果系统有ImageMagick
convert -size 81x81 xc:'#8a8a8a' monitor.png
convert -size 81x81 xc:'#00d4ff' monitor-active.png
convert -size 81x81 xc:'#8a8a8a' history.png
convert -size 81x81 xc:'#00d4ff' history-active.png

# 或者使用Python PIL
python3 << 'EOF'
from PIL import Image
import os

os.chdir('/home/gao/pro/miniprogram/images')

# 创建灰色图标
img_gray = Image.new('RGB', (81, 81), color='#8a8a8a')
img_gray.save('monitor.png')
img_gray.save('history.png')

# 创建蓝色图标
img_blue = Image.new('RGB', (81, 81), color='#00d4ff')
img_blue.save('monitor-active.png')
img_blue.save('history-active.png')

print('图标创建完成！')
EOF
```

### 2. 配置后端地址

编辑 `miniprogram/app.js` 文件，修改第6行：

```javascript
globalData: {
  baseUrl: 'https://your-domain.com',  // 改为您的实际后端地址
  // 测试阶段可以使用: 'http://localhost:4000'
  // ...
}
```

### 3. 启动后端服务

在项目根目录 `/home/gao/pro` 执行：

```bash
# 方式A：直接运行
python app.py

# 方式B：使用gunicorn（推荐）
gunicorn app:app --bind 0.0.0.0:4000
```

### 4. 编译运行

在VSCode中：
- 使用命令面板（Ctrl+Shift+P）
- 搜索"Miniprogram: Build"或"编译"
- 查看编译结果

或在微信开发者工具中：
- 点击"编译"按钮
- 查看模拟器效果

## 🔧 VSCode插件常用功能

### 命令面板命令（Ctrl+Shift+P）

- `Miniprogram: Create Project` - 创建新项目
- `Miniprogram: Open Project` - 打开项目
- `Miniprogram: Build` - 编译项目
- `Miniprogram: Preview` - 预览项目
- `Miniprogram: Upload` - 上传代码
- `Miniprogram: Set AppID` - 设置AppID

### 快捷键

- `Ctrl+S` - 保存并自动编译
- `Ctrl+B` - 快速编译

### 右键菜单

在项目文件上右键：
- 新建小程序页面
- 新建小程序组件
- 编译当前文件

## 📱 预览和调试

### 模拟器预览

在VSCode中：
- 编译成功后，插件会显示预览二维码
- 或点击底部状态栏的"预览"按钮

### 真机调试

1. 使用微信扫描预览二维码
2. 在手机上打开小程序
3. 进行真机测试

## ⚠️ 常见问题

### Q1: 插件无法识别项目

**原因**: 项目配置文件缺失或格式错误

**解决**:
- 检查 `project.config.json` 是否存在
- 检查 `app.json` 格式是否正确

### Q2: 编译失败

**原因**: 代码语法错误或配置问题

**解决**:
- 查看VSCode的"输出"面板
- 查看错误信息并修复
- 常见错误：缺少图标文件、语法错误

### Q3: 无法预览

**原因**: AppID未配置或网络问题

**解决**:
- 配置测试AppID
- 检查网络连接
- 使用微信开发者工具独立应用

### Q4: TabBar不显示

**原因**: 缺少图标文件

**解决**:
- 按照上述步骤创建图标文件
- 重新编译项目

## 📚 相关文档

- **项目文档**: `miniprogram/README.md`
- **快速开始**: `miniprogram/QUICKSTART.md`
- **图标说明**: `miniprogram/images/README.md`
- **项目总览**: `miniprogram/PROJECT_SUMMARY.md`

## 🎯 下一步

1. ✅ 在VSCode中打开 `/home/gao/pro/miniprogram` 目录
2. ⬜ 创建TabBar图标文件
3. ⬜ 配置后端地址
4. ⬜ 启动后端服务
5. ⬜ 编译并预览小程序

完成以上步骤后，您就可以开始测试小程序了！
