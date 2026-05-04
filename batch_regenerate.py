#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量重新生成有问题的基金历史数据
只重新生成价格数据可用的基金
"""
import os
import sys
import json
import time
import random
import requests
import re
from datetime import datetime

# 添加scripts目录到path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from generate_fund_history import generate_fund_history, load_fund_codes, save_history

DATA_DIR = '/home/gao/pro/fund_history'
LOG_FILE = '/home/gao/pro/logs/batch_regenerate.log'

def check_price_data_available(code):
    """检查基金的价格数据是否可用"""
    market = 'sz' if code.startswith('1') else 'sh'
    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param={market}{code},day,,,5,qfq'
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        match = re.search(r'kline_day\s*=\s*({.+})', resp.text)
        if match:
            data = json.loads(match.group(1))
            klines = data.get('data', {}).get(f'{market}{code}', {}).get('qfqday', [])
            return len(klines) > 0
    except:
        pass
    return False

def main():
    print('=' * 80)
    print('批量重新生成有问题的基金历史数据')
    print('=' * 80)
    
    # 从之前的检查日志中获取有问题的基金
    error_log = '/home/gao/pro/logs/history_check.log'
    problem_codes = set()
    
    if os.path.exists(error_log):
        with open(error_log, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('=') and ':' in line:
                    code = line.split(':')[0].strip()
                    if code and len(code) == 6 and code.isdigit():
                        problem_codes.add(code)
    
    print(f'\n发现 {len(problem_codes)} 个有问题的基金')
    
    # 检查价格数据可用性
    print(f'\n检查价格数据可用性...')
    available_codes = []
    unavailable_codes = []
    
    for i, code in enumerate(sorted(problem_codes)):
        if i % 50 == 0:
            print(f'  进度: {i}/{len(problem_codes)}')
        
        if check_price_data_available(code):
            available_codes.append(code)
        else:
            unavailable_codes.append(code)
        
        time.sleep(0.1)  # 避免请求过快
    
    print(f'\n价格数据可用的基金: {len(available_codes)} 个')
    print(f'价格数据不可用的基金: {len(unavailable_codes)} 个')
    
    if unavailable_codes:
        print(f'\n价格数据不可用的基金（前20个）: {", ".join(sorted(unavailable_codes)[:20])}')
        if len(unavailable_codes) > 20:
            print(f'... 还有 {len(unavailable_codes) - 20} 个')
    
    # 批量重新生成
    if available_codes:
        print(f'\n开始重新生成 {len(available_codes)} 个基金的数据...')
        success = 0
        failed = 0
        
        for i, code in enumerate(available_codes):
            print(f'[{i+1}/{len(available_codes)}] 处理 {code}...')
            
            try:
                data = generate_fund_history(code, days=365)
                if data:
                    save_history(code, data)
                    success += 1
                    print(f'  ✓ 成功生成 {len(data["history"])} 条')
                else:
                    failed += 1
                    print(f'  ✗ 生成失败（无数据返回）')
            except Exception as e:
                failed += 1
                print(f'  ✗ 错误: {e}')
            
            # 延迟，避免API限制
            time.sleep(random.uniform(1, 3))
        
        print(f'\n完成: 成功 {success}, 失败 {failed}')
    else:
        print('\n没有可重新生成的基金')
    
    # 保存不可用的基金列表
    unavailable_file = '/home/gao/pro/logs/unavailable_funds.txt'
    with open(unavailable_file, 'w', encoding='utf-8') as f:
        for code in sorted(unavailable_codes):
            f.write(f'{code}\n')
    print(f'\n价格数据不可用的基金列表已保存到: {unavailable_file}')

if __name__ == '__main__':
    main()
