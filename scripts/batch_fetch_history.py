#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量获取LOF基金历史数据
"""
import os
import sys
import json
import time
import random

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from fund_history import get_fund_history

LOF_CONFIG = os.path.join(BASE_DIR, 'lof_config.json')
HISTORY_DIR = os.path.join(BASE_DIR, 'fund_history')

def load_config():
    if os.path.exists(LOF_CONFIG):
        with open(LOF_CONFIG, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('funds', [])
    return []

def save_history(code, history):
    filepath = os.path.join(HISTORY_DIR, f'{code}.json')
    data = {
        'code': code,
        'days': len(history),
        'update_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'history': history
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    os.makedirs(HISTORY_DIR, exist_ok=True)
    funds = load_config()
    print(f'共 {len(funds)} 只基金需要获取历史数据')
    
    for i, fund in enumerate(funds):
        code = fund.get('code', '')
        name = fund.get('name', '')
        
        if not code:
            continue
        
        history = get_fund_history(code, 100)
        if history:
            save_history(code, history)
            print(f'[{i+1}/{len(funds)}] {code} {name}: {len(history)} 天')
        else:
            print(f'[{i+1}/{len(funds)}] {code} {name}: 获取失败')
        
        time.sleep(random.uniform(0.1, 0.3))
    
    print('完成!')

if __name__ == '__main__':
    main()