#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试：验证正确的 Referer 对东方财富净值API的影响
"""
import requests
import json

def test_api_with_referer(code, referer, description=""):
    """测试带不同Referer的API调用"""
    url = 'https://api.fund.eastmoney.com/f10/lsjz'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': referer,
    }
    params = {
        'fundCode': code,
        'pageIndex': 1,
        'pageSize': 3,
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        err_code = data.get('ErrCode')
        total_count = data.get('TotalCount', 0)
        
        # 提取第一条净值数据
        nav_list = data.get('Data', {}).get('LSJZList', [])
        first_nav = nav_list[0] if nav_list else None
        
        return {
            'code': code,
            'referer': referer,
            'description': description,
            'err_code': err_code,
            'total_count': total_count,
            'first_record': first_nav,
            'success': err_code == 0 and total_count > 0
        }
    except Exception as e:
        return {
            'code': code,
            'referer': referer,
            'description': description,
            'error': str(e),
            'success': False
        }

def main():
    print("=" * 80)
    print("测试：使用正确的 Referer 调用净值数据")
    print("=" * 80)
    
    # 测试基金列表
    test_codes = ['160125', '160105', '160216', '501018']
    
    # 测试不同的 Referer
    referers = [
        ('', '不带Referer'),
        ('https://fund.eastmoney.com/', '当前代码的Referer'),
        ('https://fundf10.eastmoney.com/', '正确Referer-域名'),
        (f'https://fundf10.eastmoney.com/jjjz_160125.html', '完整页面URL'),
    ]
    
    results = []
    
    for code in test_codes:
        print(f"\n{'='*60}")
        print(f"测试基金: {code}")
        print(f"{'='*60}")
        
        for referer, desc in referers:
            result = test_api_with_referer(code, referer, desc)
            results.append(result)
            
            status = "✓ 成功" if result['success'] else "✗ 失败"
            print(f"  {desc:30s} -> {status:10s} ErrCode: {result.get('err_code', 'N/A')}, Count: {result.get('total_count', 0)}")
            
            if result.get('first_record'):
                nav = result['first_record'].get('DWJZ', 'N/A')
                date = result['first_record'].get('FSRQ', 'N/A')
                print(f"    {'':30s}    首条记录: {date} 净值={nav}")
    
    # 总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")
    
    for code in test_codes:
        code_results = [r for r in results if r['code'] == code]
        success_referers = [r['description'] for r in code_results if r['success']]
        
        print(f"\n{code}:")
        if success_referers:
            print(f"  成功的Referer: {', '.join(success_referers)}")
        else:
            print(f"  所有Referer都失败!")
    
    # 特别验证160125
    print(f"\n{'='*60}")
    print("特别验证: 160125 (之前净值为空的基金)")
    print(f"{'='*60}")
    
    result = test_api_with_referer('160125', 'https://fundf10.eastmoney.com/', '正确Referer')
    if result['success']:
        print(f"✓ 使用正确Referer后，160125可以正常获取数据!")
        print(f"  总记录数: {result['total_count']}")
        if result['first_record']:
            print(f"  最新净值: {result['first_record'].get('DWJZ')} ({result['first_record'].get('FSRQ')})")
    else:
        print(f"✗ 即使使用正确Referer，160125仍然无法获取数据")

if __name__ == '__main__':
    main()
