#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本 - 查看实际数据格式
"""

import requests
import json

# 测试集思录数据
print("=" * 60)
print("测试集思录数据")
print("=" * 60)

url = "https://www.jisilu.cn/data/lof/stock_lof_list/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.jisilu.cn/data/lof/stock_lof_list/',
    'X-Requested-With': 'XMLHttpRequest'
}
params = {'type': 'all', 'rp': 50, 'page': 1}

response = requests.get(url, headers=headers, params=params, timeout=30)
data = response.json()

print(f"数据键: {data.keys()}")
print(f"总记录数: {data.get('total', 0)}")

if 'rows' in data and len(data['rows']) > 0:
    print(f"\n第一条记录示例:")
    first_row = data['rows'][0]
    print(json.dumps(first_row, ensure_ascii=False, indent=2))
else:
    print("rows为空或不存在")

# 测试东方财富数据
print("\n" + "=" * 60)
print("测试东方财富数据")
print("=" * 60)

url2 = "http://fund.eastmoney.com/js/fundcode_search.js"
headers2 = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://fund.eastmoney.com/'
}

response2 = requests.get(url2, headers=headers2, timeout=30)
content = response2.text

# 显示前500个字符
print(f"前500个字符:\n{content[:500]}")
