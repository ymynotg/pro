#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从集思录网站获取基金代码和基金公司的映射关系
"""

import requests
import json
import time
from typing import Dict, List

def determine_fund_type(fund_code: str, fund_name: str) -> str:
    """
    根据基金代码和名称判断基金类型
    
    Args:
        fund_code: 基金代码
        fund_name: 基金名称
    
    Returns:
        str: 基金类型 (ETF, closel, QDII, lof)
    """
    # 优先级1: ETF - 代码以159开头或名称包含ETF
    if fund_code.startswith('159') or 'ETF' in fund_name:
        return 'ETF'
    
    # 优先级2: QDII - 名称包含QDII
    if 'QDII' in fund_name or 'qdii' in fund_name.lower():
        return 'QDII'
    
    # 优先级3: closel(封闭式) - 代码以161-169开头(除了LOF)或501-502开头
    if fund_code.startswith(('161', '162', '163', '164', '165', '166', '167', '168', '169', '501', '502')):
        # 如果名称中包含LOF,则归类为LOF
        if 'LOF' in fund_name or 'lof' in fund_name.lower():
            return 'lof'
        return 'closel'
    
    # 优先级4: lof - 代码以160开头或名称包含LOF
    if fund_code.startswith('160') or 'LOF' in fund_name or 'lof' in fund_name.lower():
        return 'lof'
    
    # 默认返回空字符串(普通开放式基金)
    return ''

def get_fund_data_from_jisilu() -> Dict[str, str]:
    """
    从集思录网站获取基金数据
    
    Returns:
        Dict[str, str]: 基金代码到基金公司的映射字典
    """
    fund_mapping = {}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.jisilu.cn/',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    # 定义要获取的基金类型和对应的URL
    fund_types = [
        ('LOF基金', 'https://www.jisilu.cn/data/lof/stock_lof_list/'),
        ('ETF基金', 'https://www.jisilu.cn/data/etf/etf_list/'),
        ('封闭基金', 'https://www.jisilu.cn/data/cf/cf_list/'),
    ]
    
    try:
        print("正在从集思录获取基金数据...")
        
        for fund_type_name, url in fund_types:
            try:
                print(f"\n正在获取{fund_type_name}数据...")
                
                params = {
                    'type': 'all',
                    'rp': 100,
                    'page': 1
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # 解析数据
                if 'rows' in data:
                    count_before = len(fund_mapping)
                    for row in data['rows']:
                        # 集思录的数据结构是 row['cell']['fund_id']
                        cell = row.get('cell', {})
                        fund_code = cell.get('fund_id', '')
                        fund_name = cell.get('fund_nm', '')
                        company = cell.get('issuer_nm', '')
                        url = cell.get('urls', '')  # 基金公司官网详情页网址
                        
                        if fund_code and fund_code not in fund_mapping:
                            # 判断基金类型
                            fund_type = determine_fund_type(fund_code, fund_name)
                            
                            fund_mapping[fund_code] = {
                                'fund_name': fund_name,
                                'company': company,
                                'url': url,
                                'fund_type': fund_type  # 添加基金类型字段
                            }
                    
                    count_after = len(fund_mapping)
                    print(f"成功获取 {count_after - count_before} 条{fund_type_name}数据")
                
                # 避免请求过快
                time.sleep(0.5)
                
            except Exception as e:
                print(f"获取{fund_type_name}失败: {e}")
                continue
        
        print(f"\n集思录总共获取 {len(fund_mapping)} 条基金数据")
        
    except Exception as e:
        print(f"请求集思录API失败: {e}")
    
    return fund_mapping

def get_fund_data_from_eastmoney() -> Dict[str, str]:
    """
    从东方财富网获取基金数据（备用数据源）
    
    Returns:
        Dict[str, str]: 基金代码到基金公司的映射字典
    """
    fund_mapping = {}
    
    # 东方财富基金列表API
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'http://fund.eastmoney.com/'
    }
    
    try:
        print("正在从东方财富网获取基金数据...")
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"东方财富响应状态码: {response.status_code}")
        print(f"响应内容长度: {len(response.text)}")
        
        response.raise_for_status()
        
        # 解析JavaScript格式的数据
        content = response.text
        
        # 数据格式: var r = [["000001","HXCZHH","华夏成长混合","HUAXIACHENGZHANGHUNHE","OF-000001-华夏成长混合","华夏基金管理有限公司"],...]
        import re
        
        # 提取所有基金信息 - 修正正则表达式
        # 格式: ["基金代码","拼音缩写","基金名称","基金类型","拼音全称"]
        pattern = r'\["(\d{6})","([^"]+)","([^"]+)","([^"]+)","([^"]+)"\]'
        matches = re.findall(pattern, content)
        
        print(f"正则匹配到 {len(matches)} 条记录")
        
        if len(matches) == 0:
            # 尝试另一种格式
            print("尝试备用正则表达式...")
            pattern2 = r'\["(\d{6})","([^"]+)","([^"]+)"'
            matches = re.findall(pattern2, content)
            print(f"备用正则匹配到 {len(matches)} 条记录")
        
        for match in matches:
            fund_code = match[0]
            fund_name = match[2]
            # 东方财富的数据中没有公司信息,需要另外获取
            company = "未知"
            url = ""  # 东方财富数据中没有网址信息
            
            # 判断基金类型
            fund_type = determine_fund_type(fund_code, fund_name)
            
            fund_mapping[fund_code] = {
                'fund_name': fund_name,
                'company': company,
                'url': url,
                'fund_type': fund_type
            }
        
        print(f"成功获取 {len(fund_mapping)} 条基金数据")
        
    except Exception as e:
        print(f"从东方财富网获取数据失败: {e}")
        import traceback
        traceback.print_exc()
    
    return fund_mapping

def save_to_json(data: Dict, filename: str = "config/fund_mapping.json"):
    """
    保存数据到JSON文件
    
    Args:
        data: 要保存的数据
        filename: 文件名
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filename}")
    except Exception as e:
        print(f"保存文件失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("基金代码与基金公司映射关系获取工具")
    print("=" * 60)
    
    # 首先从东方财富获取完整的基金列表
    print("\n步骤1: 从东方财富获取完整基金列表...")
    fund_mapping = get_fund_data_from_eastmoney()
    
    # 然后从集思录获取补充公司信息
    if fund_mapping:
        print(f"\n步骤2: 从集思录补充公司信息...")
        jisilu_data = get_fund_data_from_jisilu()
        
        # 用集思录的数据补充公司信息和网址
        updated_count = 0
        for code, info in jisilu_data.items():
            if code in fund_mapping:
                if info.get('company') and info['company'] != '未知':
                    fund_mapping[code]['company'] = info['company']
                    updated_count += 1
                if info.get('url'):
                    fund_mapping[code]['url'] = info['url']
            else:
                # 如果东方财富没有,添加集思录的数据
                fund_mapping[code] = info
        
        print(f"更新了 {updated_count} 条记录的公司信息和网址")
    
    if fund_mapping:
        # 保存到JSON文件
        save_to_json(fund_mapping)
        
        # 显示部分数据示例
        print("\n数据示例（前10条）:")
        print("-" * 100)
        count = 0
        for code, info in fund_mapping.items():
            if count >= 10:
                break
            print(f"基金代码: {code}")
            print(f"基金名称: {info.get('fund_name', 'N/A')}")
            print(f"基金公司: {info.get('company', 'N/A')}")
            print(f"基金类型: {info.get('fund_type', 'N/A')}")
            print(f"公司网址: {info.get('url', 'N/A')}")
            print("-" * 100)
            count += 1
        
        print(f"\n总共获取 {len(fund_mapping)} 条基金数据")
    else:
        print("未能获取任何基金数据")

if __name__ == "__main__":
    main()
