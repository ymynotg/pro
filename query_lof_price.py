#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询LOF基金当前价 - 使用多个数据源（Tushare + 腾讯 + 东方财富）
"""

import urllib.request
import json
import re
import sys
from datetime import datetime


def get_lof_price_tushare(ts_code, token):
    """
    使用Tushare查询LOF当前价（需要2000积分）
    """
    try:
        import tushare as ts
        ts.set_token(token)
        pro = ts.pro_api()
        
        df = pro.fund_daily(ts_code=ts_code, start_date='20250101')
        
        if not df.empty:
            latest = df.iloc[0]
            return {
                'source': 'Tushare',
                'ts_code': latest['ts_code'],
                'trade_date': latest['trade_date'],
                'close': latest['close'],
                'open': latest['open'],
                'high': latest['high'],
                'low': latest['low'],
                'pre_close': latest['pre_close'],
                'change': latest['change'],
                'pct_chg': latest['pct_chg'],
                'vol': latest['vol'],
                'amount': latest['amount'],
            }
    except Exception as e:
        print(f"[Tushare] 查询失败: {e}", file=sys.stderr)
    return None


def get_lof_price_tencent(fund_code):
    """
    使用腾讯行情API查询LOF实时价格（无需积分）
    """
    market = 'sz' if fund_code.startswith('1') else 'sh'
    url = f"https://qt.gtimg.cn/q={market}{fund_code}"
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('gbk')
            fields = content.split('~')
            
            if len(fields) > 50:
                return {
                    'source': '腾讯行情',
                    'ts_code': f"{fund_code}.{market.upper()}",
                    'trade_date': fields[30] if len(fields) > 30 else datetime.now().strftime('%Y%m%d'),
                    'close': float(fields[3]) if fields[3] else 0,
                    'open': float(fields[5]) if fields[5] else 0,
                    'high': float(fields[33]) if fields[33] else 0,
                    'low': float(fields[34]) if fields[34] else 0,
                    'pre_close': float(fields[4]) if fields[4] else 0,
                    'change': float(fields[31]) if fields[31] else 0,
                    'pct_chg': float(fields[32]) if fields[32] else 0,
                    'vol': float(fields[6]) if fields[6] else 0,
                    'amount': float(fields[37]) if len(fields) > 37 and fields[37] else 0,
                }
    except Exception as e:
        print(f"[腾讯行情] 查询失败: {e}", file=sys.stderr)
    return None


def get_lof_price_eastmoney(fund_code):
    """
    使用东方财富API查询LOF实时价格（无需积分）
    """
    # 尝试多种secid格式
    secid_candidates = []
    if fund_code.startswith('1'):  # 深市
        secid_candidates = [f'0.{fund_code}', f'1.{fund_code}']
    else:  # 沪市
        secid_candidates = [f'1.{fund_code}', f'0.{fund_code}']
    
    import urllib.parse
    
    for secid in secid_candidates:
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': '101',  # 日K
            'fqt': '1',    # 前复权
            'lmt': '1',    # 只取最新一条
        }
        
        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://quote.eastmoney.com/'
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                data = json.loads(content)
                
                if data.get('data') and data['data'].get('klines'):
                    kline = data['data']['klines'][0].split(',')
                    return {
                        'source': '东方财富',
                        'ts_code': f"{fund_code}.{'SZ' if fund_code.startswith('1') else 'SH'}",
                        'trade_date': kline[0].replace('-', ''),
                        'close': float(kline[2]),
                        'open': float(kline[1]),
                        'high': float(kline[3]),
                        'low': float(kline[4]),
                        'pre_close': float(kline[2]) - float(kline[8]) if kline[8] else float(kline[2]),
                        'change': float(kline[8]) if kline[8] else 0,
                        'pct_chg': float(kline[7]) if kline[7] else 0,
                        'vol': int(kline[5]) if kline[5] else 0,
                        'amount': float(kline[6]) if kline[6] else 0,
                    }
        except Exception as e:
            continue
    
    return None


def get_lof_current_price(ts_code, token=None):
    """
    查询LOF当前价，自动尝试多个数据源
    
    Args:
        ts_code: 基金代码，如 '162411.SZ'
        token: Tushare token（可选）
    
    Returns:
        dict: 包含当前价信息的字典
    """
    # 提取纯代码
    fund_code = ts_code.split('.')[0]
    
    # 1. 先尝试Tushare（如果提供了token）
    if token:
        result = get_lof_price_tushare(ts_code, token)
        if result:
            return result
    
    # 2. 尝试腾讯行情（无需积分）
    result = get_lof_price_tencent(fund_code)
    if result:
        return result
    
    # 3. 尝试东方财富
    result = get_lof_price_eastmoney(fund_code)
    if result:
        return result
    
    print("所有数据源均查询失败", file=sys.stderr)
    return None


def print_lof_price(info):
    """格式化打印LOF价格信息"""
    if not info:
        return
    
    print(f"\n{'='*60}")
    print(f"LOF基金当前价查询")
    print(f"{'='*60}")
    print(f"基金代码: {info['ts_code']}")
    print(f"数据来源: {info.get('source', '未知')}")
    print(f"交易日期: {info['trade_date']}")
    print(f"\n【价格信息】")
    print(f"  当前价(收盘价): {info['close']:.4f} 元")
    print(f"  昨收价: {info['pre_close']:.4f} 元")
    print(f"  今开: {info['open']:.4f} 元")
    print(f"  最高: {info['high']:.4f} 元")
    print(f"  最低: {info['low']:.4f} 元")
    print(f"  涨跌额: {info['change']:.4f} 元")
    print(f"  涨跌幅: {info['pct_chg']:.2f}%")
    print(f"\n【成交信息】")
    print(f"  成交量: {int(info['vol']):,} 手")
    print(f"  成交额: {info['amount']:,.2f} 千元" if info['amount'] > 0 else f"  成交额: N/A")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    # Tushare token（可选，如果积分足够可以使用）
    TOKEN = 'a45ea803aeb581f5c484c48ecb0e3bdd29bedd43230e1c340ddadc41'
    
    # 查询162411.SZ（华宝油气LOF）
    ts_code = '162411.SZ'
    fund_code = ts_code.split('.')[0]
    
    print(f"正在查询 {ts_code} (华宝油气LOF) 的当前价...")
    print(f"提示: Tushare需要2000积分，将自动尝试其他数据源\n")
    
    # 不传入token，直接使用免费数据源
    price_info = get_lof_current_price(ts_code, token=None)
    
    if price_info:
        print_lof_price(price_info)
    else:
        print("查询失败，请检查基金代码是否正确")
