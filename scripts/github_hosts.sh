#!/bin/bash
# GitHub Hosts 优化脚本
# 用法: sudo ./github_hosts.sh

HOSTS_FILE="/etc/hosts"
GITHUB_HOSTS="
140.82.112.3 github.com
140.82.112.3 www.github.com
140.82.112.3 gist.github.com
140.82.112.4 github.com
140.82.112.4 www.github.com
140.82.112.4 gist.github.com
140.82.114.3 github.com
140.82.114.3 www.github.com
140.82.114.3 gist.github.com
140.82.114.4 github.com
140.82.114.4 www.github.com
140.82.114.4 gist.github.com
140.82.113.3 github.com
140.82.113.3 www.github.com
140.82.113.3 gist.github.com
140.82.113.4 github.com
140.82.113.4 www.github.com
140.82.113.4 gist.github.com
"

echo "添加 GitHub hosts 到 $HOSTS_FILE..."

# 备份现有 hosts
cp "$HOSTS_FILE" "${HOSTS_FILE}.bak.$(date +%Y%m%d%H%M%S)"

# 删除旧的 GitHub 相关条目
sed -i '/github.com/d' "$HOSTS_FILE"
sed -i '/www.github.com/d' "$HOSTS_FILE"
sed -i '/gist.github.com/d' "$HOSTS_FILE"

# 添加新的 hosts
echo "$GITHUB_HOSTS" >> "$HOSTS_FILE"

echo "完成！"
echo ""
echo "验证连接:"
curl -s --connect-timeout 5 https://github.com -o /dev/null -w "HTTP 状态: %{http_code}\n" && echo "成功连接 GitHub" || echo "连接失败"