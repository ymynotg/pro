#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SZSE LOF Fund List Fetcher
==========================
从深圳证券交易所获取所有LOF基金列表

数据源: https://www.szse.cn/api/report/ShowReport/data
CATALOGID: 1945_LOF

功能:
    - 获取所有LOF基金列表（代码、名称、规模、管理人）
    - 获取最新净值信息
    - 支持分页获取
"""

import sys
import json
import re
import requests
from datetime import datetime

API_URL = 'https://www.szse.cn/api/report/ShowReport/data'

def get_lof_list(page=1, page_size=10):
    """
    获取LOF基金列表（分页）
    
    Args:
        page (int): 页码，默认1
        page_size (int): 每页数量，默认10
    
    Returns:
        dict: {
            'total': int,      # 总数
            'page': int,        # 当前页
            'page_size': int,    # 每页数量
            'page_count': int,  # 总页数
            'funds': list       # 基金列表
        }
    """
    params = {
        'SHOWTYPE': 'JSON',
        'CATALOGID': '1945_LOF',
        'loading': 'first' if page == 1 else 'normal',
        'page': page,
        'pageSize': page_size,
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.szse.cn/market/product/list/lofFundList/index.html',
    }
    
    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=30)
        data = resp.json()
        
        if data and data[0].get('metadata'):
            meta = data[0]['metadata']
            records = data[0].get('data', [])
            
            funds = []
            for r in records:
                # 提取代码
                code_match = re.search(r'>([0-9]+)<', r.get('sys_key', ''))
                code = code_match.group(1) if code_match else ''
                
                # 提取名称
                name_match = re.search(r'<u>([^<]+)</u>', r.get('kzjcurl', ''))
                name = name_match.group(1) if name_match else ''
                
                funds.append({
                    'code': code,
                    'name': name,
                    'scale': r.get('dqgm', ''),           # 规模
                    'manager': r.get('glrmc', ''),         # 管理人
                    'index': r.get('nhzs', '').strip(),   # 拟合指数
                })
            
            return {
                'total': meta.get('recordcount', 0),
                'page': meta.get('pageno', page),
                'page_size': page_size,
                'page_count': meta.get('pagecount', 0),
                'funds': funds,
            }
    except Exception as e:
        print(f"Error: {e}")
    
    return None


def get_all_lof_list():
    """
    获取所有LOF基金列表
    
    Returns:
        list: [{'code': str, 'name': str, 'scale': str, 'manager': str, 'index': str}, ...]
    """
    all_funds = []
    page = 1
    page_size = 50
    
    while True:
        result = get_lof_list(page, page_size)
        if not result or not result.get('funds'):
            break
        
        all_funds.extend(result['funds'])
        print(f"已获取第 {page} 页 ({len(result['funds'])} 条), 总计 {len(all_funds)}/{result['total']}")
        
        if page >= result.get('page_count', 1):
            break
        page += 1
    
    return all_funds


def get_lof_with_nav():
    """
    获取所有LOF基金及最新净值
    
    Returns:
        list: [{'code': str, 'name': str, 'nav': float, 'date': str}, ...]
    """
    # 先获取所有LOF列表
    funds = get_all_lof_list()
    
    # 使用1785_child获取净值
    nav_params = {
        'SHOWTYPE': 'JSON',
        'CATALOGID': '1945_LOF',
        'TABKEY': 'tab2',
    }
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.szse.cn/',
    }
    
    try:
        resp = requests.get(API_URL, params=nav_params, headers=headers, timeout=30)
        data = resp.json()
        
        if data and len(data) > 1:
            nav_data = data[1].get('data', [])
            nav_map = {}
            for item in nav_data:
                code = item.get('fund_code', '')
                nav_map[code] = {
                    'nav': float(item.get('nav_per_share', 0)),
                    'date': item.get('nav_date', ''),
                }
            
            for fund in funds:
                code = fund['code']
                if code in nav_map:
                    fund['nav'] = nav_map[code]['nav']
                    fund['nav_date'] = nav_map[code]['date']
    except Exception as e:
        print(f"Error getting nav: {e}")
    
    return funds


if __name__ == '__main__':
    print("SZSE LOF 基金列表获取工具")
    print("=" * 50)
    
    # 获取所有LOF
    print("\n正在获取LOF列表...")
    funds = get_all_lof_list()
    
    print(f"\n共获取 {len(funds)} 只LOF基金")
    print("\n前10只:")
    print("-" * 50)
    for f in funds[:10]:
        print(f"{f['code']}: {f['name']} | 规模: {f['scale']}万份 | 管理人: {f['manager']}")