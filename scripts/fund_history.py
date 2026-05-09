#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import requests
import time
import random
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import configparser

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'fund_history.log')
LOG_CONF_FILE = os.path.join(BASE_DIR, 'config', 'logging.conf')

def load_log_level():
    if os.path.exists(LOG_CONF_FILE):
        try:
            config = configparser.ConfigParser()
            config.read(LOG_CONF_FILE)
            if 'log' in config and 'level' in config['log']:
                return getattr(logging, config['log']['level'].strip().upper(), logging.INFO)
        except:
            pass
    return logging.INFO

def setup_logger(name='fund_history'):
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(load_log_level())
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        fh = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger

logger = setup_logger()

def get_fund_realtime(code):
    """
    获取基金实时数据(当日净值和估算价格)
    数据来源: https://fundgz.1234567.com.cn/js/{code}.js
    
    返回字段说明:
    - price: 估算价格(gsz)
    - nav: 基金单位净值(dwjz)
    - valuation: 估算价格(同gsz)
    - change: 涨跌幅(净值涨跌幅)
    - update_time: 更新时间
    """
    logger.info(f"获取基金实时数据: {code}")
    import datetime
    url = f'https://fundgz.1234567.com.cn/js/{code}.js?rt={int(datetime.datetime.now().timestamp())}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://fund.eastmoney.com/',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200 and 'jsonpgz' in resp.text:
            import re
            match = re.search(r'jsonpgz\(({.+})\)', resp.text)
            if match:
                data = json.loads(match.group(1))
                return {
                    'price': float(data.get('gsz', 0)),
                    'change': float(data.get('gszzf', 0)),  # 修复字段名: gszzl -> gszzf
                    'nav': float(data.get('dwjz', 0)),
                    'valuation': float(data.get('gsz', 0)),
                    'update_time': data.get('gztime', ''),
                }
    except Exception as e:
        logger.warning(f"获取实时数据失败 {code}: {e}")
    return None

def get_market_price(code, days=1):
    """
    获取LOF基金二级市场交易价格
    数据来源: https://web.ifzq.gtimg.cn
    """
    import re
    price_map = {}
    try:
        market = 'sz' if code.startswith('1') else 'sh'
        url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param={market}{code},day,,,{days},qfq'
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        match = re.search(r'kline_day\s*=\s*({.+})', resp.text)
        if match:
            data = json.loads(match.group(1))
            klines = data.get('data', {}).get(f'{market}{code}', {}).get('qfqday', [])
            for item in klines:
                if len(item) >= 5:
                    date = item[0]
                    close = float(item[2]) if item[2] else 0
                    if close > 0:
                        price_map[date] = close
    except Exception as e:
        logger.warning(f"获取市场交易价格失败 {code}: {e}")
    return price_map

def get_fund_history_from_detail(code, days=30):
    """
    获取基金历史数据（净值+交易价格）
    价格数据来自腾讯K线接口（完整历史），估值来自天天基金（仅实时）
    """
    try:
        realtime = get_fund_realtime(code)
        price_map = get_price_from_tencent(code, 500)
        
        if not price_map:
            logger.warning(f"{code}: 无K线数据")
            return []
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_price = price_map.get(today, 0)
        nav = realtime.get('nav', 0) if realtime else 0
        valuation = realtime.get('valuation', 0) if realtime else 0

        result = []
        dates = sorted(price_map.keys(), reverse=True)[:days]
        for i, date in enumerate(dates):
            price = price_map[date]
            premium = ((price - nav) / nav * 100) if nav > 0 and price > 0 else 0

            if i < len(dates) - 1:
                prev_price = price_map[dates[i + 1]]
                chg = round((price - prev_price) / prev_price * 100, 2)
            else:
                chg = 0

            result.append({
                'date': date,
                'nav': round(nav, 4) if nav > 0 else '',
                'valuation': round(valuation, 4) if valuation > 0 else '',
                'price': round(price, 4),
                'change': chg,
                'premium': round(premium, 2) if premium else '',
            })
        
        logger.info(f"{code}: 成功获取 {len(result)} 条历史数据")
        return result
        
    except Exception as e:
        logger.error(f"{code}: 获取失败 - {str(e)}")
    return []

def get_price_from_tencent(code, days=30):
    """
    从腾讯获取LOF基金二级市场交易价格
    数据来源: https://web.ifzq.gtimg.cn
    API: /appstock/app/fqkline/get
    返回: 二级市场每日收盘价
    
    参数:
        code: 基金代码
        days: 获取天数
    返回:
        dict: {日期: 价格}
    """
    import re
    price_map = {}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        # 判断交易所: 深市代码以1开头, 沪市代码以5开头
        if code.startswith('1'):
            market = 'sz'
        else:
            market = 'sh'
        
        # 腾讯前复权日K线接口
        url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param={market}{code},day,,,{days},qfq'
        logger.debug(f"{code}: 请求腾讯K线接口 - {url[:60]}...")
        
        resp = requests.get(url, headers=headers, timeout=15)
        
        match = re.search(r'kline_day\s*=\s*({.+})', resp.text)
        if match:
            data = json.loads(match.group(1))
            klines = data.get('data', {}).get(f'{market}{code}', {}).get('qfqday', [])
            
            for item in klines:
                if len(item) >= 5:
                    date = item[0]
                    close = float(item[2]) if item[2] else 0
                    if close > 0:
                        price_map[date] = close
            
            logger.debug(f"{code}: 腾讯接口返回 {len(price_map)} 条价格记录")
        else:
            logger.warning(f"{code}: 腾讯接口返回数据解析失败")
    except Exception as e:
        logger.warning(f"{code}: 获取腾讯价格失败 - {str(e)}")
    
    return price_map


def get_realtime_price_from_tencent(code):
    """
    从腾讯获取LOF基金实时交易价格（盘中实时数据）
    数据来源: https://qt.gtimg.cn
    API: /q=sz{code} 或 /q=sh{code}
    返回: 包含当前价、涨跌幅等实时数据
    """
    import re
    try:
        market = 'sz' if code.startswith('1') else 'sh'
        url = f'https://qt.gtimg.cn/q={market}{code}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            content = resp.text
            match = re.search(r'="(.+)"', content)
            if match:
                fields = match.group(1).split('~')
                if len(fields) > 32:
                    return {
                        'current_price': float(fields[3]) if fields[3] else 0,
                        'yesterday_close': float(fields[4]) if fields[4] else 0,
                        'open_price': float(fields[5]) if fields[5] else 0,
                        'change_amount': float(fields[31]) if fields[31] else 0,
                        'change_percent': float(fields[32]) if fields[32] else 0,
                        'high': float(fields[33]) if fields[33] else 0,
                        'low': float(fields[34]) if fields[34] else 0,
                    }
    except Exception as e:
        logger.warning(f"{code}: 获取腾讯实时价格失败 - {str(e)}")
    return None

def get_fund_history(code, days=30):
    logger.info(f"获取基金历史数据: {code}, days={days}")
    
    result = get_fund_history_from_detail(code, days)
    
    if not result:
        logger.warning(f"{code} 无历史数据，使用实时数据")
        realtime = get_fund_realtime(code)
        today = datetime.now().strftime('%Y-%m-%d')
        nav = realtime.get('nav', 0) if realtime else 0
        valuation = realtime.get('valuation', 0) if realtime else 0
        change = realtime.get('change', '') if realtime else ''
        
        # 使用腾讯实时接口获取当前价
        realtime_price_data = get_realtime_price_from_tencent(code)
        if realtime_price_data:
            price = realtime_price_data.get('current_price', 0)
            # 如果使用实时价格的涨跌幅，可以用这个
            # change = realtime_price_data.get('change_percent', change)
        else:
            # 备用：使用历史价格接口获取最近价格
            price_map = get_price_from_tencent(code, 1)
            price = price_map.get(today, 0)
        
        premium = ((price - nav) / nav * 100) if nav > 0 and price > 0 else 0
        result = [{
            'date': today,
            'nav': nav if nav > 0 else '',
            'valuation': valuation if valuation > 0 else '',
            'price': round(price, 4) if price > 0 else '',
            'change': change,
            'premium': round(premium, 2) if premium else '',
        }]
    
    logger.info(f"{code} 获取到 {len(result)} 条历史数据")
    return result

def get_funds_history(codes, days=30):
    results = {}
    for code in codes:
        history = get_fund_history(code, days)
        if history:
            results[code] = history
        time.sleep(random.uniform(0.1, 0.3))
    return results

def get_fund_info(code):
    url = f'https://fund.eastmoney.com/pingzhongdata/{code}.js'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://fund.eastmoney.com/',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            text = resp.text
            import re
            name_match = re.search(r'var fS_name = "([^"]+)"', text)
            code_match = re.search(r'var fS_code = "([^"]+)"', text)
            return {
                'code': code_match.group(1) if code_match else code,
                'name': name_match.group(1) if name_match else '',
            }
    except Exception as e:
        logger.warning(f"获取基金信息失败 {code}: {e}")
    return {'code': code, 'name': ''}

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        code = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        
        print(f"获取 {code} 最近 {days} 天历史数据...\n")
        history = get_fund_history(code, days)
        
        if history:
            print(f"{'日期':<12} {'收盘价':<10} {'涨跌幅':<10} {'净值':<10} {'估值':<10} {'溢价率':<10}")
            print("-" * 62)
            for item in history:
                print(f"{item['date']:<12} {item['price']:<10.4f} {item['change']:>+9.2f}% {item['nav']:<10.4f} {item['valuation']:<10.4f} {item['premium']:>+9.2f}%")
        else:
            print("未获取到数据")
    else:
        print("用法: python fund_history.py <基金代码> [天数]")
        print("示例: python fund_history.py 161039 30")