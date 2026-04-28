#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SZSE Fund Price Fetcher
======================
从深圳证券交易所(SZSE)获取LOF基金净值数据

数据源: https://www.szse.cn/api/report/ShowReport/data
CATALOGID: 1785_child (基金净值)

输入:
    - code: 6位基金代码 (str)
    
输出:
    - code: 基金代码
    - name: 基金简称
    - nav: 单位净值 (元)
    - date: 净值日期
    
返回格式: dict 或 None (获取失败时)
"""

import sys
import json
import requests

API_URL = 'https://www.szse.cn/api/report/ShowReport/data'

def get_szse_fund_price(code):
    """
    获取SZSE基金净值数据
    
    Args:
        code (str): 6位基金代码，如 '163118'
    
    Returns:
        dict: {
            'code': str,      # 基金代码
            'name': str,      # 基金简称
            'nav': float,     # 单位净值(元)
            'date': str       # 净值日期 YYYY-MM-DD
        }
        None: 获取失败时返回None
    """
    params = {
        'SHOWTYPE': 'JSON',
        'CATALOGID': '1785_child',
        'TABKEY': 'tab1',
        'txtDm': code,
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.szse.cn/',
    }
    
    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=10)
        data = resp.json()
        
        if data and data[0].get('data'):
            latest = data[0]['data'][0]
            return {
                'code': latest.get('fund_code', ''),
                'name': latest.get('security_short_name', ''),
                'nav': float(latest.get('nav_per_share', 0)),
                'date': latest.get('nav_date', ''),
            }
    except Exception as e:
        print(f"Error: {e}")
    
    return None


def get_szse_fund_history(code, days=30):
    """
    获取SZSE基金历史净值
    
    Args:
        code (str): 6位基金代码
        days (int): 获取天数，默认30天
    
    Returns:
        list: [{'date': str, 'nav': float}, ...]
    """
    params = {
        'SHOWTYPE': 'JSON',
        'CATALOGID': '1785_child',
        'TABKEY': 'tab1',
        'txtDm': code,
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.szse.cn/',
    }
    
    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=10)
        data = resp.json()
        
        if data and data[0].get('data'):
            history = []
            for item in data[0]['data'][:days]:
                history.append({
                    'date': item.get('nav_date', ''),
                    'nav': float(item.get('nav_per_share', 0)),
                })
            return history
    except Exception as e:
        print(f"Error: {e}")
    
    return []


def get_batch_prices(codes):
    """
    批量获取多个基金净值
    
    Args:
        codes (list): 基金代码列表
    
    Returns:
        dict: {code: {'code': str, 'name': str, 'nav': float, 'date': str}, ...}
    """
    results = {}
    for code in codes:
        result = get_szse_fund_price(code)
        if result:
            results[code] = result
    return results


if __name__ == '__main__':
    # 命令行调用示例
    if len(sys.argv) > 1:
        code = sys.argv[1]
        result = get_szse_fund_price(code)
        
        if result:
            print("=" * 40)
            print(f"基金代码: {result['code']}")
            print(f"基金简称: {result['name']}")
            print(f"单位净值: {result['nav']:.4f} 元")
            print(f"净值日期: {result['date']}")
            print("=" * 40)
        else:
            print("获取失败，请检查基金代码")
    else:
        print("SZSE基金净值查询工具")
        print("=" * 40)
        print("用法:")
        print("  python szse_price.py <基金代码>")
        print("")
        print("示例:")
        print("  python szse_price.py 163118")
        print("  python szse_price.py 160726")
        print("")
        print("输出:")
        print("  基金代码: 163118")
        print("  基金简称: 医药生物LOF")
        print("  单位净值: 0.6526 元")
        print("  净值日期: 2026-04-21")