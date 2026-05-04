#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量检查历史数据问题
"""
import os
import json
import requests
import re
from datetime import datetime
from collections import defaultdict

DATA_DIR = '/home/gao/pro/fund_history'
ERROR_LOG = '/home/gao/pro/logs/history_check.log'

def check_file(file_path):
    """检查单个历史数据文件"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        code = data.get('code', 'unknown')
        history = data.get('history', [])
        
        if not history:
            issues.append(f'{code}: 无历史数据')
            return issues
        
        # 1. 检查nav为空的记录
        nav_empty_count = sum(1 for item in history if not item.get('nav'))
        if nav_empty_count > 0:
            issues.append(f'{code}: {nav_empty_count}/{len(history)} 条记录nav为空 ({nav_empty_count/len(history)*100:.1f}%)')
        
        # 2. 检查日期连续性
        dates = [item.get('date') for item in history if item.get('date')]
        if dates:
            date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
            date_objects_sorted = sorted(date_objects, reverse=True)
            
            # 检查是否有重复日期
            if len(dates) != len(set(dates)):
                issues.append(f'{code}: 存在重复日期')
            
            # 检查日期排序
            if dates != [d.strftime('%Y-%m-%d') for d in date_objects_sorted]:
                issues.append(f'{code}: 日期未按时间倒序排列')
        
        # 3. 检查price为空的记录
        price_empty_count = sum(1 for item in history if not item.get('price'))
        if price_empty_count > 0:
            issues.append(f'{code}: {price_empty_count} 条记录price为空')
        
        # 4. 检查update_time是否过旧
        update_time = data.get('update_time', '')
        if update_time:
            try:
                update_dt = datetime.strptime(update_time, '%Y-%m-%d %H:%M:%S')
                days_old = (datetime.now() - update_dt).days
                if days_old > 7:
                    issues.append(f'{code}: 数据已过期 {days_old} 天（{update_time}）')
            except:
                pass
        
        # 5. 检查days字段是否与实际历史记录数一致
        if data.get('days') != len(history):
            issues.append(f'{code}: days字段({data.get("days")})与实际记录数({len(history)})不一致')
        
    except Exception as e:
        issues.append(f'{os.path.basename(file_path)}: 文件读取失败 - {e}')
    
    return issues

def get_all_fund_codes():
    """获取所有基金代码"""
    codes = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            codes.append(filename.replace('.json', ''))
    return sorted(codes)

def batch_check_nav_availability(codes, sample_size=20):
    """抽样检查基金净值API的可用性"""
    print(f'\n抽样检查 {sample_size} 个基金的净值API可用性...')
    
    # 抽样：选择一些可能有问题的基金
    sample_codes = codes[:sample_size] if len(codes) > sample_size else codes
    
    url = 'https://api.fund.eastmoney.com/f10/lsjz'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://fund.eastmoney.com/',
    }
    
    results = []
    for code in sample_codes:
        try:
            params = {
                'fundCode': code,
                'pageIndex': 1,
                'pageSize': 5,
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            if data.get('Data') and data['Data'].get('LSJZList'):
                results.append((code, True, len(data['Data']['LSJZList'])))
            else:
                results.append((code, False, 0))
        except:
            results.append((code, False, 0))
    
    success_count = sum(1 for _, success, _ in results if success)
    print(f'  成功: {success_count}/{len(results)}')
    
    if success_count < len(results):
        print(f'  API不可用的基金:')
        for code, success, count in results:
            if not success:
                print(f'    {code}')

def main():
    print('=' * 80)
    print('全量检查历史数据问题')
    print('=' * 80)
    
    # 获取所有基金代码
    codes = get_all_fund_codes()
    print(f'\n共发现 {len(codes)} 个基金历史数据文件')
    
    # 全量检查每个文件
    print(f'\n开始检查每个文件...')
    all_issues = defaultdict(list)
    
    for i, code in enumerate(codes):
        if i % 50 == 0:
            print(f'  进度: {i}/{len(codes)}')
        
        file_path = os.path.join(DATA_DIR, f'{code}.json')
        issues = check_file(file_path)
        
        for issue in issues:
            # 提取问题类型
            if 'nav为空' in issue:
                all_issues['nav_empty'].append(issue)
            elif '重复日期' in issue:
                all_issues['duplicate_dates'].append(issue)
            elif '日期未按时间倒序' in issue:
                all_issues['wrong_order'].append(issue)
            elif 'price为空' in issue:
                all_issues['price_empty'].append(issue)
            elif '已过期' in issue:
                all_issues['outdated'].append(issue)
            elif '不一致' in issue:
                all_issues['days_mismatch'].append(issue)
            else:
                all_issues['other'].append(issue)
    
    # 输出检查结果
    print('\n' + '=' * 80)
    print('检查结果汇总')
    print('=' * 80)
    
    for issue_type, issues in all_issues.items():
        print(f'\n{issue_type} ({len(issues)} 个):')
        for issue in issues[:10]:  # 只显示前10个
            print(f'  {issue}')
        if len(issues) > 10:
            print(f'  ... 还有 {len(issues) - 10} 个')
    
    # 重点：检查nav为空的基金
    if all_issues.get('nav_empty'):
        print('\n' + '=' * 80)
        print('重点问题：nav为空的基金')
        print('=' * 80)
        
        nav_empty_codes = [item.split(':')[0] for item in all_issues['nav_empty']]
        print(f'\n共 {len(nav_empty_codes)} 个基金存在nav为空的问题')
        print(f'基金代码: {", ".join(nav_empty_codes[:20])}')
        if len(nav_empty_codes) > 20:
            print(f'... 还有 {len(nav_empty_codes) - 20} 个')
    
    # 保存详细日志
    os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)
    with open(ERROR_LOG, 'w', encoding='utf-8') as f:
        f.write('全量检查历史数据问题\n')
        f.write(f'检查时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'检查文件数: {len(codes)}\n\n')
        
        for issue_type, issues in all_issues.items():
            f.write(f'\n{issue_type} ({len(issues)} 个):\n')
            for issue in issues:
                f.write(f'  {issue}\n')
    
    print(f'\n详细日志已保存到: {ERROR_LOG}')
    
    # 抽样检查API可用性
    batch_check_nav_availability(codes)
    
    print('\n' + '=' * 80)
    print('检查完成')
    print('=' * 80)

if __name__ == '__main__':
    main()
