#!/bin/bash

# 微信开发者工具安装脚本（Linux/Wine版本）
# 适用于Ubuntu/Debian系统

set -e

echo "========================================="
echo "微信开发者工具 Linux安装脚本"
echo "========================================="
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
  echo "请使用sudo运行此脚本"
  echo "用法: sudo bash $0"
  exit 1
fi

# 步骤1：安装Wine
echo "步骤1：安装Wine..."
echo ""

if ! command -v wine &> /dev/null; then
    echo "正在安装Wine..."
    apt update
    apt install -y wine64 wine32 winetricks

    echo "Wine安装完成！"
    wine --version
else
    echo "Wine已安装：$(wine --version)"
fi

echo ""

# 步骤2：配置Wine
echo "步骤2：配置Wine..."
echo ""

# 创建Wine配置目录
WINEPREFIX="/home/$SUDO_USER/.wine"
export WINEPREFIX

echo "Wine配置目录: $WINEPREFIX"
echo ""

# 初始化Wine（这会创建默认配置）
if [ ! -d "$WINEPREFIX" ]; then
    echo "初始化Wine配置..."
    sudo -u $SUDO_USER wineboot --init
fi

echo ""

# 步骤3：安装必要的Windows组件
echo "步骤3：安装Windows组件..."
echo ""

echo "安装中文字体..."
sudo -u $SUDO_USER winetricks wqy-zenhei || true

echo "安装Visual C++运行库..."
sudo -u $SUDO_USER winetricks vcrun2015 || true

echo ""

# 步骤4：下载微信开发者工具
echo "步骤4：下载微信开发者工具..."
echo ""

DOWNLOAD_DIR="/home/$SUDO_USER/Downloads"
mkdir -p "$DOWNLOAD_DIR"

TOOL_FILE="$DOWNLOAD_DIR/wechat_devtools.exe"

if [ ! -f "$TOOL_FILE" ]; then
    echo "正在下载微信开发者工具..."
    echo "下载地址：https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html"
    echo ""

    # 下载最新稳定版
    wget -O "$TOOL_FILE" \
        "https://dldir1.qq.com/WechatWebDev/release/be1ec64cf6184b0fa6c9a6e567ca5987/wechat_devtools_1.06.2307260_x64.exe" \
        || {
            echo "下载失败！"
            echo "请手动下载："
            echo "1. 访问 https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html"
            echo "2. 下载Windows 64位版本"
            echo "3. 保存到: $DOWNLOAD_DIR"
            exit 1
        }

    chown $SUDO_USER:$SUDO_USER "$TOOL_FILE"
    echo "下载完成！"
else
    echo "微信开发者工具已存在: $TOOL_FILE"
fi

echo ""

# 步骤5：安装微信开发者工具
echo "步骤5：安装微信开发者工具..."
echo ""

echo "正在安装，请稍候..."
echo "注意：安装过程中可能会弹出Windows风格的对话框，请按提示操作"
echo ""

sudo -u $SUDO_USER wine "$TOOL_FILE" /SILENT || true

echo ""

# 步骤6：创建启动脚本
echo "步骤6：创建启动脚本..."
echo ""

START_SCRIPT="/home/$SUDO_USER/start-wechat-devtools.sh"

cat > "$START_SCRIPT" << 'EOF'
#!/bin/bash

# 微信开发者工具启动脚本

export WINEPREFIX="$HOME/.wine"

# 查找微信开发者工具可执行文件
TOOL_PATH=$(find "$WINEPREFIX/drive_c/Program Files" -name "wechat_devtools.exe" 2>/dev/null | head -1)

if [ -z "$TOOL_PATH" ]; then
    # 尝试其他可能的位置
    TOOL_PATH=$(find "$WINEPREFIX/drive_c/Program Files (x86)" -name "wechat_devtools.exe" 2>/dev/null | head -1)
fi

if [ -z "$TOOL_PATH" ]; then
    echo "错误：找不到微信开发者工具"
    echo "请确认已正确安装"
    exit 1
fi

echo "启动微信开发者工具..."
echo "路径: $TOOL_PATH"
echo ""

wine "$TOOL_PATH"
EOF

chmod +x "$START_SCRIPT"
chown $SUDO_USER:$SUDO_USER "$START_SCRIPT"

echo "启动脚本已创建: $START_SCRIPT"
echo ""

# 步骤7：创建项目导入指南
echo "步骤7：创建项目导入指南..."
echo ""

GUIDE_FILE="/home/$SUDO_USER/pro/miniprogram/IMPORT_GUIDE.txt"

cat > "$GUIDE_FILE" << 'EOF'
========================================
微信开发者工具项目导入指南
========================================

1. 启动微信开发者工具
   运行: ~/start-wechat-devtools.sh

2. 导入项目
   - 点击"导入项目"或"+"按钮
   - 项目目录输入: Z:\home\gao\pro\miniprogram
     (Wine中Linux路径映射为Z盘)
   - AppID: 留空或使用测试号
   - 项目名称: 基金套利监控
   - 点击"确定"

3. 配置后端
   - 打开 app.js 文件
   - 修改 baseUrl 为您的后端地址
   - 例如: http://localhost:4000

4. 启动后端服务
   cd /home/gao/pro
   python app.py

5. 开始开发
   - 编辑代码
   - 编译项目
   - 预览效果

========================================
常见问题
========================================

Q: 找不到项目路径？
A: Wine路径映射规则：
   Linux: /home/gao/pro/miniprogram
   Wine:  Z:\home\gao\pro\miniprogram

Q: 中文显示乱码？
A: 已自动安装中文字体，如仍有问题：
   cp /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc ~/.wine/drive_c/windows/Fonts/

Q: 无法启动？
A: 尝试重新安装：
   wine ~/.wine/drive_c/Program\ Files/微信web开发者工具/wechat_devtools.exe

========================================
EOF

chown $SUDO_USER:$SUDO_USER "$GUIDE_FILE"

echo "导入指南已创建: $GUIDE_FILE"
echo ""

# 完成
echo "========================================="
echo "✅ 安装完成！"
echo "========================================="
echo ""
echo "下一步操作："
echo ""
echo "1. 启动微信开发者工具："
echo "   ~/start-wechat-devtools.sh"
echo ""
echo "2. 导入项目："
echo "   项目路径: Z:\\home\\gao\\pro\\miniprogram"
echo ""
echo "3. 查看详细指南："
echo "   cat ~/pro/miniprogram/IMPORT_GUIDE.txt"
echo ""
echo "4. 查看完整文档："
echo "   cat ~/pro/miniprogram/LINUX_SOLUTION.md"
echo ""
echo "========================================="
