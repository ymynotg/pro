#!/usr/bin/env python3
"""
基金数据获取脚本 - 162411 华宝油气LOF
"""

import urllib.request
import json
import re
import sys
from datetime import datetime


def fetch_fund_estimate(fund_code: str) -> dict:
    """获取基金实时估算数据（东方财富API）"""
    url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js?rt={int(datetime.now().timestamp())}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            json_str = re.search(r'\((.+)\)', content)
            if json_str:
                return json.loads(json_str.group(1))
    except Exception as e:
        print(f"[ERROR] 获取基金估算数据失败: {e}", file=sys.stderr)
    return {}


def fetch_fund_realtime(fund_code: str) -> dict:
    """获取基金实时场内交易数据（腾讯行情API）"""
    url = f"https://qt.gtimg.cn/q=sz{fund_code}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('gbk')
            fields = content.split('~')
            if len(fields) > 50:
                return {
                    'current_price': fields[3],
                    'yesterday_close': fields[4],
                    'open_price': fields[5],
                    'volume': fields[6],
                    'change_amount': fields[31],
                    'chaget_qdii_realtime_from_tencentnge_percent': fields[32],
                    'high': fields[33],
                    'low': fields[34],
                }
    except Exception as e:
        print(f"[ERROR] 获取场内实时数据失效: {e}", file=sys.stderr)
    return {}


def fetch_subscription_status(fund_code: str) -> dict:
    """获取基金申赎状态（天天基金基本信息页面）"""
    url = f"https://fundf10.eastmoney.com/jbgk_{fund_code}.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://fund.eastmoney.com/'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            
            # 提取申购状态
            subscribe_match = re.search(r'交易状态：<span>([^<]+)</span>', content)
            subscribe_status = subscribe_match.group(1).strip() if subscribe_match else ''
            
            # 提取赎回状态
            redeem_match = re.search(r'<span[^>]*>(开放赎回|暂停赎回|限制赎回)</span>', content)
            redeem_status = redeem_match.group(1).strip() if redeem_match else ''
            
            # 提取限制金额
            limit_amount = ''
            amount_match = re.search(r'单日累计购买上限([\d.]+)(万|元)', content)
            if amount_match:
                num_str = amount_match.group(1)
                unit = amount_match.group(2)
                num = float(num_str)
                # 去掉无意义的小数
                if num == int(num):
                    num_str = str(int(num))
                else:
                    num_str = f'{num:g}'
                limit_amount = f'{num_str}{unit}'
            
            return {
                'subscription_status': subscribe_status,
                'redemption_status': redeem_status,
                'limit_amount': limit_amount
            }
    except Exception as e:
        print(f"[ERROR] 获取申赎状态失败: {e}", file=sys.stderr)
    
    return {'subscription_status': '', 'redemption_status': ''}


def fetch_tencent_kline_with_change(fund_code: str, days: int = 30) -> dict:
    """用腾讯K线收盘价计算历史涨跌幅（无需新接口）"""
    import re
    
    market = 'sz' if fund_code.startswith('1') else 'sh'
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param={market}{fund_code},day,,,{days},qfq"
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            match = re.search(r'kline_day\s*=\s*({.+})', content)
            if match:
                data = json.loads(match.group(1))
                klines = data.get('data', {}).get(f'{market}{fund_code}', {}).get('qfqday', [])
                
                # 按日期正序排列，计算涨跌幅
                klines_sorted = sorted(klines, key=lambda x: x[0])
                result = []
                prev_close = None
                
                for item in klines_sorted:
                    if len(item) >= 3:
                        date = item[0]
                        close = float(item[2])
                        
                        if prev_close:
                            change_pct = round((close - prev_close) / prev_close * 100, 2)
                        else:
                            change_pct = None  # 首条无涨跌幅
                        
                        result.append({
                            'date': date,
                            'close': close,
                            'change_pct': change_pct,
                        })
                        prev_close = close
                
                return {'success': True, 'code': fund_code, 'data': list(reversed(result))}  # 倒序返回，最新在前
    except Exception as e:
        print(f"[ERROR] 腾讯K线计算涨跌幅失败: {e}", file=sys.stderr)
    
    return {'success': False, 'message': '腾讯K线获取失败'}


def fetch_eastmoney_kline(fund_code: str, days: int = 30) -> dict:
    """获取基金历史K线数据（东方财富接口，直接含涨跌幅）"""
    import urllib.parse
    
    # 尝试多种可能的secid格式
    secid_candidates = []
    if fund_code.startswith('1'):  # 深市LOF
        secid_candidates = [f'0.{fund_code}', f'1.{fund_code}', f'8.{fund_code}', f'90.{fund_code}']
    else:  # 沪市LOF
        secid_candidates = [f'1.{fund_code}', f'0.{fund_code}', f'8.{fund_code}', f'90.{fund_code}']
    
    for secid in secid_candidates:
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': '101',   # 日K线
            'fqt': '1',     # 前复权
            'lmt': str(days),
        }
        
        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://quote.eastmoney.com/'
            })
            print(f"[DEBUG] req:[req]")
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                
                data = json.loads(content)
                
                if data.get('data') and data['data'].get('klines'):
                    klines = data['data']['klines']
                    result = []
                    for line in klines:
                        fields = line.split(',')
                        result.append({
                            'date': fields[0],
                            'open': float(fields[1]),
                            'close': float(fields[2]),
                            'high': float(fields[3]),
                            'low': float(fields[4]),
                            'volume': int(fields[5]),
                            'amount': float(fields[6]),
                            'change_pct': float(fields[7]),  # f58: 涨跌幅(%)
                            'change_amt': float(fields[8]),  # f59: 涨跌额
                        })
                    print(f"[INFO] 成功使用 secid={secid}", file=sys.stderr)
                    return {'success': True, 'code': fund_code, 'data': result, 'secid': secid}
                else:
                    print(f"[DEBUG] secid={secid} 无数据, 响应: {content[:200]}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] secid={secid} 失败: {e}", file=sys.stderr)
    
    return {'success': False, 'message': '所有secid格式均失败'}


def main(fund_code: str = "162411"):
    estimate = fetch_fund_estimate(fund_code)
    realtime = fetch_fund_realtime(fund_code)
    subscription = fetch_subscription_status(fund_code)

    print(f"\n{'='*60}")
    print(f"基金代码: {fund_code} - 华宝标普石油天然气上游股票指数(LOF)")
    print(f"{'='*60}")

    print(f"\n【净值信息】")
    print(f"  单位净值: {estimate.get('dwjz', 'N/A')}")
    print(f"  累计净值: {estimate.get('ljjz', 'N/A')}")
    print(f"  净值更新: {estimate.get('gztime', 'N/A')}")

    gsz = estimate.get('gsz', 'N/A')
    gszzf = estimate.get('gszzf', '')
    if gszzf and gszzf not in ['--', '']:
        print(f"\n【估值信息】")
        print(f"  估算净值: {gsz}")
        print(f"  估算涨跌幅: {gszzf}%")
    else:
        print(f"\n【估值信息】")
        print(f"  估算净值: 盘中暂无估值（QDII基金需待美股收盘后更新）")
        print(f"  估算涨跌幅: N/A")

    print(f"\n【场内交易 - 实时行情】")
    if realtime:
        print(f"  当前价(最新价): {realtime.get('current_price', 'N/A')} 元")
        print(f"  涨跌幅: {realtime.get('change_percent', 'N/A')}%")
        print(f"  涨跌额: {realtime.get('change_amount', 'N/A')} 元")
        print(f"  今开: {realtime.get('open_price', 'N/A')} 元")
        print(f"  最高: {realtime.get('high', 'N/A')} 元")
        print(f"  最低: {realtime.get('low', 'N/A')} 元")
        print(f"  成交量: {int(float(realtime.get('volume', 0))):,} 手")
    else:
        print(f"  暂无可用数据")

    print(f"\n【申赎状态】")
    print(f"  申购状态: {subscription.get('subscription_status', 'N/A')}")
    if subscription.get('limit_amount'):
        print(f"  限制金额: {subscription['limit_amount']}")
    print(f"  赎回状态: {subscription.get('redemption_status', 'N/A')}")

    # 东方财富K线历史数据
    print(f"\n【历史K线数据 - 东方财富接口】")
    kline_data = fetch_eastmoney_kline(fund_code, days=10)
    print(f"[我的debug]:Kline_data:[{kline_data}]")
    if kline_data.get('success'):
        history = kline_data['data']
        print(f"  共 {len(history)} 条历史数据")
        print(f"\n  {'日期':<12} {'开盘':<8} {'收盘':<8} {'最高':<8} {'最低':<8} {'成交量':<12} {'涨跌幅':<8}")
        print(f"  {'-'*70}")
        for item in reversed(history):  # 倒序显示，最新在前
            print(f"  {item['date']:<12} {item['open']:<8.3f} {item['close']:<8.3f} "
                  f"{item['high']:<8.3f} {item['low']:<8.3f} {item['volume']:<12} {item['change_pct']:>+7.2f}%")
    else:
        print(f"  获取失败: {kline_data.get('message', '未知错误')}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "000041"
    main(code)