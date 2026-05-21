# TabBar 图标说明

本目录需要放置以下图标文件，用于小程序底部导航栏：

## 图标要求

- **尺寸**: 81x81 像素
- **格式**: PNG格式，支持透明背景
- **颜色**: 建议使用单色图标

## 需要的图标文件

1. **monitor.png** - 监控图标（未选中状态）
   - 建议颜色: #8a8a8a（灰色）
   - 图标样式: 仪表盘或图表图标

2. **monitor-active.png** - 监控图标（选中状态）
   - 建议颜色: #00d4ff（蓝色）
   - 图标样式: 与未选中状态相同，但颜色不同

3. **history.png** - 历史图标（未选中状态）
   - 建议颜色: #8a8a8a（灰色）
   - 图标样式: 时钟或历史记录图标

4. **history-active.png** - 历史图标（选中状态）
   - 建议颜色: #00d4ff（蓝色）
   - 图标样式: 与未选中状态相同，但颜色不同

## 图标制作建议

### 方案一：使用在线工具
- [iconfont](https://www.iconfont.cn/) - 阿里巴巴矢量图标库
- [Flaticon](https://www.flaticon.com/) - 免费图标资源
- [Icons8](https://icons8.com/) - 图标设计工具

### 方案二：使用设计软件
- Figma
- Sketch
- Adobe Illustrator

### 方案三：临时方案（开发测试用）
可以使用纯色方块作为临时图标：
- 创建81x81的PNG图片
- 未选中状态填充灰色 (#8a8a8a)
- 选中状态填充蓝色 (#00d4ff)

## 快速生成临时图标（使用ImageMagick）

如果系统安装了ImageMagick，可以使用以下命令快速生成：

```bash
# 进入images目录
cd /home/gao/pro/miniprogram/images

# 生成监控图标（灰色）
convert -size 81x81 xc:'#8a8a8a' monitor.png

# 生成监控图标（蓝色）
convert -size 81x81 xc:'#00d4ff' monitor-active.png

# 生成历史图标（灰色）
convert -size 81x81 xc:'#8a8a8a' history.png

# 生成历史图标（蓝色）
convert -size 81x81 xc:'#00d4ff' history-active.png
```

## 注意事项

1. 图标文件必须放在 `miniprogram/images/` 目录下
2. 文件名必须与 `app.json` 中的配置一致
3. 建议使用简洁、清晰的图标设计
4. 确保图标在不同设备上显示清晰
