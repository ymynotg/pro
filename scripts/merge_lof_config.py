#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOF配置文件合并脚本
=================
将深市LOF和沪市LOF配置文件合并生成lof_config.json

功能:
    - 读取深市配置文件 (config/szse_lof_config.json)
    - 读取沪市配置文件 (config/sse_lof_config.json)
    - 合并生成新的lof_config.json
    - 备份原lof_config.json到backups目录
    - source字段标记为"证券官网"

配置文件格式(lof_config.json):
    {
        "update_time": "2024-01-01",
        "count": 404,
        "funds": [
            {
                "code": "501001",
                "name": "财通多策略精选混合(LOF)",
                "type": "SHLOF",
                "source": "证券官网",
                "update_time": "2024-01-01 12:00:00"
            },
            ...
        ]
    }

使用方式:
    python3 merge_lof_config.py
"""

import sys
import os
import json
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
BACKUPS_DIR = os.path.join(BASE_DIR, 'backups')

SZSE_CONFIG = os.path.join(CONFIG_DIR, 'szse_lof_config.json')
SSE_CONFIG = os.path.join(CONFIG_DIR, 'sse_lof_config.json')
OUTPUT_CONFIG = os.path.join(BASE_DIR, 'lof_config.json')


def merge_configs():
    """合并深市和沪市LOF配置"""
    print("开始合并LOF配置文件...")
    
    # 读取深市配置
    with open(SZSE_CONFIG, 'r', encoding='utf-8') as f:
        szse_data = json.load(f)
    print(f"深市LOF: {len(szse_data)}只")
    
    # 读取沪市配置
    with open(SSE_CONFIG, 'r', encoding='utf-8') as f:
        sse_data = json.load(f)
    print(f"沪市LOF: {len(sse_data)}只")
    
    # 转换格式并合并
    funds = []
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 处理深市LOF (1xx开头)
    for fund in szse_data:
        funds.append({
            'code': fund['代码'],
            'name': fund['名称'],
            'type': 'SZLOF',
            'source': '证券官网',
            'update_time': update_time
        })
    
    # 处理沪市LOF (5xx开头)
    for fund in sse_data:
        funds.append({
            'code': fund['代码'],
            'name': fund['名称'],
            'type': 'SHLOF',
            'source': '证券官网',
            'update_time': update_time
        })
    
    # 按代码排序
    funds.sort(key=lambda x: x['code'])
    
    # 生成新配置
    merged = {
        'update_time': update_time,
        'count': len(funds),
        'funds': funds
    }
    
    return merged


def main():
    """主函数"""
    print("=" * 60)
    print("LOF配置文件合并脚本启动")
    print("=" * 60)
    
    # 备份原文件
    if os.path.exists(OUTPUT_CONFIG):
        backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BACKUPS_DIR, f'lof_config.json.bak_{backup_time}')
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        shutil.copy2(OUTPUT_CONFIG, backup_file)
        print(f"已备份原文件到: {backup_file}")
    
    # 合并配置
    merged = merge_configs()
    
    # 保存新配置
    with open(OUTPUT_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"合并完成: {merged['count']}只LOF")
    print(f"配置文件: {OUTPUT_CONFIG}")
    print("=" * 60)
    
    # 统计
    szlof = sum(1 for f in merged['funds'] if f['type'] == 'SZLOF')
    shlof = sum(1 for f in merged['funds'] if f['type'] == 'SHLOF')
    print(f"  深市LOF (SZLOF): {szlof}只")
    print(f"  沪市LOF (SHLOF): {shlof}只")
    print(f"  总计: {szlof + shlof}只")


if __name__ == '__main__':
    main()