#!/bin/bash
# GitHub hosts 优化脚本
# 用法: sudo ./update_github_hosts.sh

GITHUB_IPS=(
    "140.82.112.3"
    "140.82.112.4"
    "140.82.114.3"
    "140.82.114.4"
    "140.82.113.3"
    "140.82.113.4"
)

HOSTS_FILE="/etc/hosts"
MARKER="# GitHub hosts"

echo "正在更新 GitHub hosts..."

for ip in "${GITHUB_IPS[@]}"; do
    if ! grep -q "$ip" "$HOSTS_FILE" 2>/dev/null; then
        echo "$ip github.com" >> "$HOSTS_FILE"
        echo "$ip www.github.com" >> "$HOSTS_FILE"
        echo "$ip gist.github.com" >> "$HOSTS_FILE"
    fi
done

echo "完成！"
echo ""
echo "验证连接:"
curl -s --connect-timeout 5 https://github.com -o /dev/null && echo "GitHub 可访问" || echo "GitHub 不可访问"