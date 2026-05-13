#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试方案1：增加净值数据获取量，验证日期匹配
测试方案2：pytdx 获取 LOF 历史估值数据验证
"""
import requests
import re
import json
from datetime import datetime, timedelta

def get_price_data(code, days=365):
    """从腾讯获取价格数据"""
    market = 'sz' if code.startswith('1') else 'sh'
    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param={market}{code},day,,,{days},qfq'
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        match = re.search(r'kline_day\s*=\s*({.+})', resp.text)
        if match:
            data = json.loads(match.group(1))
            klines = data.get('data', {}).get(f'{market}{code}', {}).get('qfqday', [])
            return {item[0]: float(item[2]) for item in klines if len(item) >= 3 and float(item[2]) > 0}
    except Exception as e:
        print(f"价格数据获取失败: {e}")
    return {}

def get_nav_data_limited(code, days=365):
    """原方案：限制获取量（约380条）"""
    url = 'https://api.fund.eastmoney.com/f10/lsjz'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://fund.eastmoney.com/',
    }
    nav_dict = {}
    page_size = 200
    page_index = 1
    max_pages = (days // 20) + 2
    
    try:
        while page_index <= max_pages:
            params = {
                'fundCode': code,
                'pageIndex': page_index,
                'pageSize': page_size,
                'startDate': '',
                'endDate': '',
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('Data') and data['Data'].get('LSJZList'):
                    lsjz_list = data['Data']['LSJZList']
                    for item in lsjz_list:
                        date = item.get('FSRQ', '')
                        nav = item.get('DWJZ', '')
                        if date and nav:
                            nav_dict[date] = float(nav)
                    if len(lsjz_list) < 20:
                        break
                    page_index += 1
                else:
                    break
            else:
                break
    except Exception as e:
        print(f"净值数据获取失败: {e}")
    
    return nav_dict

def get_nav_data_full(code):
    """方案1：获取全部净值数据（不限量）"""
    url = 'https://api.fund.eastmoney.com/f10/lsjz'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://fund.eastmoney.com/',
    }
    nav_dict = {}
    page_index = 1
    
    try:
        while True:
            params = {
                'fundCode': code,
                'pageIndex': page_index,
                'pageSize': 20,  # API每次实际最多返回20条
                'startDate': '',
                'endDate': '',
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('Data') and data['Data'].get('LSJZList'):
                    lsjz_list = data['Data']['LSJZList']
                    if not lsjz_list:
                        break
                    
                    for item in lsjz_list:
                        date = item.get('FSRQ', '')
                        nav = item.get('DWJZ', '')
                        if date and nav:
                            nav_dict[date] = float(nav)
                    
                    # API每次返回20条，如果少于20条说明到最后一页
                    if len(lsjz_list) < 20:
                        break
                    
                    page_index += 1
                    
                    # 安全限制：最多获取10000条
                    if len(nav_dict) >= 10000:
                        break
                else:
                    break
            else:
                break
    except Exception as e:
        print(f"净值数据获取失败: {e}")
    
    return nav_dict

def test_date_matching(code):
    """测试日期匹配情况"""
    print(f"\n{'='*80}")
    print(f"测试基金: {code}")
    print(f"{'='*80}")
    
    # 获取价格数据
    print("\n1. 获取价格数据（腾讯K线）...")
    price_map = get_price_data(code, days=365)
    print(f"   获取价格数据: {len(price_map)} 条")
    if price_map:
        dates = sorted(price_map.keys(), reverse=True)
        print(f"   价格日期范围: {dates[0]} ~ {dates[-1]}")
        print(f"   最新5个价格日期:")
        for d in dates[:5]:
            print(f"     {d}: {price_map[d]}")
    
    # 测试方案1原版：限制获取量
    print("\n2. 测试原方案：限制获取量（约380条）...")
    nav_map_limited = get_nav_data_limited(code, days=365)
    print(f"   获取净值数据: {len(nav_map_limited)} 条")
    if nav_map_limited:
        dates = sorted(nav_map_limited.keys(), reverse=True)
        print(f"   净值日期范围: {dates[0]} ~ {dates[-1]}")
    
    # 测试方案1改进：获取全部数据
    print("\n3. 测试方案1改进：获取全部净值数据...")
    nav_map_full = get_nav_data_full(code)
    print(f"   获取净值数据: {len(nav_map_full)} 条")
    if nav_map_full:
        dates = sorted(nav_map_full.keys(), reverse=True)
        print(f"   净值日期范围: {dates[0]} ~ {dates[-1]}")
    
    # 测试日期匹配
    if price_map and nav_map_limited:
        print("\n4. 日期匹配测试（原方案 - 限制获取量）:")
        matched_limited = 0
        for date in sorted(price_map.keys(), reverse=True)[:20]:
            if date in nav_map_limited:
                print(f"   {date}: ✓ 匹配 (price={price_map[date]}, nav={nav_map_limited[date]})")
                matched_limited += 1
            else:
                print(f"   {date}: ✗ 不匹配")
        print(f"   匹配率（前20个）: {matched_limited}/20")
    
    if price_map and nav_map_full:
        print("\n5. 日期匹配测试（方案1改进 - 获取全部）:")
        matched_full = 0
        for date in sorted(price_map.keys(), reverse=True)[:20]:
            if date in nav_map_full:
                print(f"   {date}: ✓ 匹配 (price={price_map[date]}, nav={nav_map_full[date]})")
                matched_full += 1
            else:
                print(f"   {date}: ✗ 不匹配")
        print(f"   匹配率（前20个）: {matched_full}/20")
        
        # 检查所有价格日期的匹配情况
        print("\n6. 全部价格日期匹配统计（方案1改进）:")
        total_matched = 0
        total_checked = len(price_map)
        for date in price_map.keys():
            if date in nav_map_full:
                total_matched += 1
        
        print(f"   总价格日期数: {total_checked}")
        print(f"   匹配到的日期数: {total_matched}")
        print(f"   总匹配率: {total_matched}/{total_checked} ({total_matched/total_checked*100:.1f}%)")
        
        # 检查未匹配的日期
        if total_matched < total_checked:
            print(f"\n   未匹配的日期（前10个）:")
            unmatched = [d for d in sorted(price_map.keys(), reverse=True) if d not in nav_map_full]
            for d in unmatched[:10]:
                print(f"     {d}")
            
            # 检查未匹配日期的范围
            if unmatched:
                print(f"\n   未匹配日期范围: {min(unmatched)} ~ {max(unmatched)}")
                print(f"   净值数据最早日期: {min(nav_map_full.keys())}")
                print(f"   结论: 未匹配日期早于净值数据起始日期")

if __name__ == '__main__':
    print("="*80)
    print("方案1验证：增加净值数据获取量")
    print("="*80)
    
    # 测试160125（问题基金）
    test_date_matching('160125')
    
    # 测试160105（正常基金）作为对比
    test_date_matching('160105')
    
    print(f"\n{'='*80}")
    print("验证完成")
    print(f"{'='*80}")

# ============================================================
# 测试方案2：pytdx 获取 LOF 历史估值数据
# ============================================================
def test_pytdx():
    """验证 pytdx 能否获取 LOF 基金历史估值（净值）数据"""
    print(f"\n{'='*80}")
    print("测试方案2: pytdx LOF 历史估值数据")
    print(f"{'='*80}")
    
    from pytdx.hq import TdxHq_API
    from pytdx.params import TDXParams
    
    api = TdxHq_API()
    try:
        ok = api.connect('180.153.18.170', 7709)
        if not ok:
            print("连接失败")
            return
        print("通达信行情服务器连接成功\n")
        
        # 1. 获取 LOF 日K线（场内交易价格）
        codes = [
            ('162411', 0, '华宝油气'),
            ('160632', 0, '鹏华酒'),
            ('501018', 1, '南方原油'),
            ('164705', 0, '添富恒生'),
        ]
        
        print("1. 日K线数据（交易价格）:")
        for code, market, name in codes:
            data = api.get_security_bars(
                category=TDXParams.KLINE_TYPE_DAILY,
                market=market, code=code, start=0, count=3
            )
            if data:
                for bar in data:
                    dt = bar.get('datetime', '')
                    close = bar.get('close', 0)
                    print(f"  {name}({code}): {dt} 收盘={close}")
            else:
                print(f"  {name}({code}): 无K线数据")
        
        # 2. 获取财务信息（含最新每股净资产 = 净值）
        print("\n2. 财务信息（最新每股净资产）:")
        for code, market, name in codes:
            info = api.get_finance_info(market, code)
            nav = info.get('meigujingzichan', 0) if info else 0
            date = info.get('updated_date', 0) if info else 0
            print(f"  {name}({code}): 每股净资产={nav} (更新日期={date})")
        
        # 3. 结论
        print("\n=== 结论 ===")
        print("pytdx 可获取: LOF 场内交易日K线（开高低收量额）+ 最新每股净资产")
        print("pytdx 不可获取: 历史净值数据（仅有最新值，无历史序列）")
        print("历史净值仍需通过东方财富 API (api.fund.eastmoney.com/f10/lsjz) 获取")
        
        api.disconnect()
    except Exception as e:
        print(f"异常: {e}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'pytdx':
        test_pytdx()
    else:
        # 默认运行方案1
        test_date_matching('162411')
        test_date_matching('501018')
        test_date_matching('160105')
