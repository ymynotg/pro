# Linux系统微信小程序开发快速指南

## 🐧 您的系统环境

- **操作系统**: Linux (Ubuntu)
- **架构**: amd64 (已支持i386)
- **问题**: 微信开发者工具不支持Linux

## ✅ 解决方案：使用Wine运行Windows版

### 快速安装（推荐）

#### 方法一：使用自动安装脚本

```bash
cd /home/gao/pro/miniprogram
sudo bash install-wine.sh
```

脚本会自动完成：
1. ✅ 安装Wine
2. ✅ 配置Windows环境
3. ✅ 下载微信开发者工具
4. ✅ 安装必要组件
5. ✅ 创建启动脚本

#### 方法二：手动安装

```bash
# 1. 安装Wine
sudo apt update
sudo apt install wine64 wine32 winetricks

# 2. 下载微信开发者工具
cd ~/Downloads
wget -O wechat_devtools.exe "https://dldir1.qq.com/WechatWebDev/release/be1ec64cf6184b0fa6c9a6e567ca5987/wechat_devtools_1.06.2307260_x64.exe"

# 3. 安装
wine wechat_devtools.exe

# 4. 安装中文字体（解决乱码）
winetricks wqy-zenhei
```

### 启动微信开发者工具

```bash
# 使用自动创建的启动脚本
~/start-wechat-devtools.sh

# 或手动启动
wine ~/.wine/drive_c/Program\ Files/微信web开发者工具/wechat_devtools.exe
```

### 导入项目

在微信开发者工具中：

1. **点击"导入项目"**

2. **填写项目信息**：
   - 项目目录：`Z:\home\gao\pro\miniprogram`
     - ⚠️ 注意：Wine中Linux路径映射为Z盘
   - AppID：留空或使用测试号
   - 项目名称：基金套利监控

3. **点击"确定"**

### 配置后端

编辑 `app.js` 文件：

```javascript
globalData: {
  baseUrl: 'http://localhost:4000',  // 本地测试
  // 或
  baseUrl: 'https://your-domain.com',  // 正式环境
  // ...
}
```

启动后端：

```bash
cd /home/gao/pro
python app.py
# 或
gunicorn app:app --bind 0.0.0.0:4000
```

## 📂 路径映射规则

Wine中的路径映射：

| Linux路径 | Wine路径 |
|-----------|----------|
| `/home/gao/pro/miniprogram` | `Z:\home\gao\pro\miniprogram` |
| `/home/gao/Downloads` | `Z:\home\gao\Downloads` |
| `~/.wine/drive_c` | `C:\` |

## 🔧 常见问题解决

### Q1: Wine安装失败

```bash
# 确保已启用32位架构
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install wine64 wine32
```

### Q2: 微信开发者工具无法启动

```bash
# 安装必要的Windows组件
winetricks corefonts vcrun2015

# 或使用Windows 7模式
winecfg
# 在"Windows版本"中选择"Windows 7"
```

### Q3: 中文显示乱码

```bash
# 安装中文字体
winetricks wqy-zenhei

# 或手动复制字体
cp /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc ~/.wine/drive_c/windows/Fonts/
```

### Q4: 找不到项目路径

确保使用正确的Wine路径格式：
- ✅ 正确：`Z:\home\gao\pro\miniprogram`
- ❌ 错误：`/home/gao/pro/miniprogram`

### Q5: 性能较慢

Wine运行Windows程序会有一定性能损失，这是正常的。建议：
- 关闭不必要的后台应用
- 增加系统内存
- 使用SSD硬盘

## 🎯 替代方案

如果Wine方案不适合您，可以考虑：

### 方案一：在线开发平台

- **微信云开发**: https://developers.weixin.qq.com/miniprogram/dev/wxcloud/basis/getting-started.html
- 无需本地工具，在线编辑和预览

### 方案二：虚拟机

```bash
# 安装VirtualBox
sudo apt install virtualbox

# 创建Windows虚拟机
# 安装微信开发者工具
# 设置共享文件夹
```

### 方案三：远程Windows

- 使用远程桌面连接到Windows机器
- 在Windows上开发

## 📱 开发流程

### 1. 编辑代码
- 使用VSCode（已打开项目）
- 或使用微信开发者工具内置编辑器

### 2. 编译预览
- 在微信开发者工具中点击"编译"
- 查看模拟器效果

### 3. 真机测试
- 点击"预览"生成二维码
- 使用微信扫码
- 在手机上测试

### 4. 上传发布
- 点击"上传"
- 填写版本信息
- 在微信公众平台提交审核

## 📚 相关文档

- `LINUX_SOLUTION.md` - Linux解决方案详细说明
- `install-wine.sh` - 自动安装脚本
- `README.md` - 项目完整文档
- `QUICKSTART.md` - 快速开始指南

## 🚀 快速开始步骤

1. **安装Wine和微信开发者工具**
   ```bash
   sudo bash /home/gao/pro/miniprogram/install-wine.sh
   ```

2. **启动微信开发者工具**
   ```bash
   ~/start-wechat-devtools.sh
   ```

3. **导入项目**
   - 项目路径：`Z:\home\gao\pro\miniprogram`
   - AppID：留空

4. **配置后端**
   - 修改 `app.js` 中的 `baseUrl`
   - 启动后端服务

5. **开始开发**
   - 编辑代码
   - 编译预览
   - 真机测试

## ✅ 检查清单

开始前请确认：
- [ ] Wine已安装
- [ ] 微信开发者工具已安装
- [ ] 中文字体已安装
- [ ] 项目路径正确（使用Wine格式）
- [ ] 后端地址已配置
- [ ] 后端服务已启动

---

**创建时间**: 2026-05-21
**适用系统**: Linux (Ubuntu/Debian)
**推荐方案**: Wine运行Windows版微信开发者工具
