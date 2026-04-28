#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复历史数据文件中的price字段"""
import json
import os
import re
import requests
from glob import glob

HISTORY_DIR = 'fund_history'

def get_price_map(code, days=100):
    """从腾讯获取正确的收盘价"""
    market = 'sz' if code.startswith('1') else 'sh'
    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param={market}{code},day,,,{days},qfq'
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        match = re.search(r'kline_day\s*=\s*({.+})', resp.text)
        if match:
            data = json.loads(match.group(1))
            klines = data.get('data', {}).get(f'{market}{code}', {}).get('qfqday', [])
            price_map = {}
            for item in klines:
                if len(item) >= 5:
                    date = item[0]
                    close = float(item[2]) if item[2] else 0
                    if close > 0:
                        price_map[date] = close
            return price_map
    except Exception as e:
        print(f"  获取 {code} 价格失败: {e}")
    return {}

def fix_file(filepath):
    """修复单个文件"""
    code = os.path.basename(filepath).replace('.json', '')
    print(f"处理 {code}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'history' not in data:
        print(f"  {code}: 无 history 字段，跳过")
        return

    price_map = get_price_map(code, 100)
    if not price_map:
        print(f"  {code}: 无法获取价格数据，跳过")
        return

    fixed_count = 0
    for item in data['history']:
        date = item.get('date')
        if date and date in price_map:
            item['price'] = round(price_map[date], 4)
            fixed_count += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  {code}: 修复 {fixed_count} 条记录")

def main():
    files = glob(os.path.join(HISTORY_DIR, '*.json'))
    print(f"找到 {len(files)} 个历史数据文件\n")

    for filepath in sorted(files):
        fix_file(filepath)

    print("\n完成!")

if __name__ == '__main__':
    main()