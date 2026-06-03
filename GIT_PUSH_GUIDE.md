# Git推送指南

## 📊 当前状态

✅ **提交已创建成功！**
- 提交ID: 3fba687
- 提交内容: 30个文件，4289行新增代码
- 提交信息: "feat: 添加微信小程序版本"

❌ **推送失败原因**: 需要GitHub认证

## 🔐 解决方案

### 方案一：使用SSH方式推送（推荐）

#### 1. 检查SSH密钥

```bash
ls -la ~/.ssh
```

如果没有SSH密钥，创建一个：

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

#### 2. 添加SSH密钥到GitHub

```bash
# 查看公钥
cat ~/.ssh/id_ed25519.pub
```

然后：
1. 登录GitHub: https://github.com
2. 进入 Settings → SSH and GPG keys → New SSH key
3. 粘贴公钥内容
4. 保存

#### 3. 修改远程仓库为SSH地址

```bash
git remote set-url origin git@github.com:ymynotg/pro.git
```

#### 4. 推送

```bash
git push origin master
```

### 方案二：使用Personal Access Token

#### 1. 创建GitHub Token

1. 登录GitHub: https://github.com
2. 进入 Settings → Developer settings → Personal access tokens → Tokens (classic)
3. 点击 "Generate new token (classic)"
4. 勾选权限：repo（完整仓库权限）
5. 生成并复制token

#### 2. 配置Git使用Token

```bash
# 方式A：在推送时输入token作为密码
git push origin master
# Username: ymynotg
# Password: <your_token>

# 方式B：在URL中包含token
git remote set-url origin https://<token>@github.com/ymynotg/pro.git
git push origin master

# 方式C：配置credential helper
git config --global credential.helper store
git push origin master
# 输入用户名和token，会自动保存
```

### 方案三：使用GitHub CLI（最简单）

#### 1. 安装GitHub CLI

```bash
# Ubuntu/Debian
sudo apt install gh

# 或使用snap
sudo snap install gh
```

#### 2. 登录GitHub

```bash
gh auth login
```

按提示选择：
- GitHub.com
- HTTPS
- Login with a web browser

#### 3. 推送

```bash
git push origin master
```

## 🚀 快速推送（推荐方案）

### 如果您已有SSH密钥：

```bash
# 1. 修改远程地址为SSH
git remote set-url origin git@github.com:ymynotg/pro.git

# 2. 推送
git push origin master
```

### 如果您想使用Token：

```bash
# 1. 在GitHub创建Personal Access Token
# 2. 推送时使用token
git push origin master
# Username: ymynotg
# Password: <your_token>
```

### 如果您想安装GitHub CLI：

```bash
# 1. 安装
sudo apt install gh

# 2. 登录
gh auth login

# 3. 推送
git push origin master
```

## 📋 推送后验证

推送成功后，访问您的GitHub仓库：
https://github.com/ymynotg/pro

应该能看到：
- ✅ 新的提交记录
- ✅ miniprogram目录
- ✅ 30个新文件

## 🔍 检查当前配置

```bash
# 查看远程仓库
git remote -v

# 查看最近提交
git log -1 --oneline

# 查看待推送的提交
git log origin/master..HEAD --oneline
```

## ⚠️ 常见问题

### Q1: Permission denied (publickey)

**原因**: SSH密钥未添加到GitHub

**解决**:
1. 查看公钥：`cat ~/.ssh/id_ed25519.pub`
2. 添加到GitHub: Settings → SSH and GPG keys

### Q2: Authentication failed

**原因**: Token无效或权限不足

**解决**:
1. 重新生成Token
2. 确保勾选了repo权限

### Q3: remote: Repository not found

**原因**: 仓库地址错误或无权限

**解决**:
1. 检查仓库地址：`git remote -v`
2. 确认有仓库写入权限

## 📊 提交信息

本次提交包含：

**新增文件（30个）**:
- 小程序核心文件（app.js, app.json, app.wxss）
- 页面文件（index, history）
- 工具类（api.js, request.js, util.js）
- 图标资源（4个PNG文件）
- 文档文件（8个MD文件）
- 配置文件（project.config.json等）

**代码统计**:
- 新增行数: 4289行
- 涉及文件: 30个

**功能特性**:
- ✅ 完整的小程序项目结构
- ✅ LOF/QDII/ETF/期权数据展示
- ✅ 搜索筛选功能
- ✅ 历史数据图表
- ✅ 深色主题
- ✅ 完整文档

## 🎯 下一步

1. **选择认证方式**（推荐SSH或GitHub CLI）
2. **配置认证**
3. **执行推送**
4. **验证结果**

---

**创建时间**: 2026-05-21
**提交ID**: 3fba687
**待推送**: 是
