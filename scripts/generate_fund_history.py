#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import time
import random
import logging
from logging.handlers import RotatingFileHandler
import configparser
from datetime import datetime
import requests
import re

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'generate_history.log')
DATA_DIR = os.path.join(BASE_DIR, 'fund_history')
LOF_CONFIG = os.path.join(BASE_DIR, 'lof_config.json')
QDII_CONFIG = os.path.join(BASE_DIR, 'qdii_config.json')
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

def setup_logger(name='generate_history'):
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

def get_tencent_kline(code, days=365):
    """从腾讯获取K线数据"""
    market = 'sz' if code.startswith('1') else 'sh'
    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param={market}{code},day,,,{days},qfq'
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        match = re.search(r'kline_day\s*=\s*({.+})', resp.text)
        if match:
            data = json.loads(match.group(1))
            code_data = data.get('data', {}).get(f'{market}{code}', {})
            klines = code_data.get('qfqday', []) or code_data.get('day', [])
            return {item[0]: float(item[2]) for item in klines if len(item) >= 3 and float(item[2]) > 0}
    except Exception as e:
        logger.warning(f"{code}: 腾讯K线获取失败 - {e}")
    return {}

def get_fund_realtime(code):
    """从天天基金获取实时估值"""
    url = f'https://fundgz.1234567.com.cn/js/{code}.js'
    try:
        resp = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://fund.eastmoney.com/'
        }, timeout=10)
        if 'jsonpgz' in resp.text and resp.text != 'jsonpgz();':
            match = re.search(r'jsonpgz\((.+)\)', resp.text)
            if match:
                data = json.loads(match.group(1))
                return {
                    'nav': float(data.get('dwjz', 0)),
                    'valuation': float(data.get('gsz', 0)),
                    'change': float(data.get('gszzl', 0)),
                }
    except:
        pass
    return None

def generate_fund_history(code, days=365):
    """生成单只基金历史数据"""
    price_map = get_tencent_kline(code, days)
    if not price_map:
        return None

    realtime = get_fund_realtime(code)
    nav = realtime.get('nav', 0) if realtime else 0
    valuation = realtime.get('valuation', 0) if realtime else 0

    dates = sorted(price_map.keys(), reverse=True)[:days]
    history = []
    for date in dates:
        price = price_map[date]
        premium = ((price - nav) / nav * 100) if nav > 0 and price > 0 else 0
        history.append({
            'date': date,
            'nav': round(nav, 4) if nav > 0 else '',
            'valuation': round(valuation, 4) if valuation > 0 else '',
            'price': round(price, 4),
            'change': realtime.get('change', '') if realtime else '',
            'premium': round(premium, 2) if premium else '',
        })

    return {
        'code': code,
        'days': len(history),
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'history': history
    }

def save_history(code, data):
    """保存历史数据到文件"""
    history_file = os.path.join(DATA_DIR, f'{code}.json')
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_fund_codes():
    """加载所有基金代码（LOF + QDII）"""
    codes = []

    if os.path.exists(LOF_CONFIG):
        with open(LOF_CONFIG, 'r', encoding='utf-8') as f:
            config = json.load(f)
            for fund in config.get('funds', []):
                codes.append(fund.get('code'))

    if os.path.exists(QDII_CONFIG):
        with open(QDII_CONFIG, 'r', encoding='utf-8') as f:
            config = json.load(f)
            for fund in config.get('funds', []):
                codes.append(fund.get('code'))

    return list(set(codes))

def update_fund_history(code, days=365, incremental=True):
    """更新单只基金历史数据
    
    Args:
        code: 基金代码
        days: 获取天数（仅全量时生效）
        incremental: True增量更新，False全量替换
    """
    history_file = os.path.join(DATA_DIR, f'{code}.json')
    
    if incremental and os.path.exists(history_file):
        # 增量更新：读取现有数据，只更新最新一天
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            # 获取最新数据
            price_map = get_tencent_kline(code, 1)
            if not price_map:
                return None
            
            realtime = get_fund_realtime(code)
            nav = realtime.get('nav', 0) if realtime else 0
            valuation = realtime.get('valuation', 0) if realtime else 0
            
            # 检查今天是否已有数据
            today = datetime.now().strftime('%Y-%m-%d')
            if old_data['history'] and old_data['history'][0]['date'] == today:
                logger.info(f"{code}: 今天数据已存在，跳过")
                return old_data
            
            # 添加今天的数据
            for date, price in price_map.items():
                premium = ((price - nav) / nav * 100) if nav > 0 and price > 0 else 0
                old_data['history'].insert(0, {
                    'date': date,
                    'nav': round(nav, 4) if nav > 0 else '',
                    'valuation': round(valuation, 4) if valuation > 0 else '',
                    'price': round(price, 4),
                    'change': realtime.get('change', '') if realtime else '',
                    'premium': round(premium, 2) if premium else '',
                })
            
            old_data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            old_data['days'] = len(old_data['history'])
            
            return old_data
        except Exception as e:
            logger.warning(f"{code}: 增量更新失败，转为全量 - {e}")
    
    # 全量生成
    return generate_fund_history(code, days)


def generate_all_history(days=365, incremental=False):
    """生成或更新所有基金历史数据
    
    Args:
        days: 全量生成时的天数
        incremental: True增量更新，False全量替换
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    codes = load_fund_codes()
    logger.info(f"开始{'增量更新' if incremental else '全量生成'}历史数据，共 {len(codes)} 只基金")

    success = 0
    failed = 0

    for i, code in enumerate(codes):
        logger.info(f"[{i+1}/{len(codes)}] 处理 {code}")

        data = update_fund_history(code, days, incremental)

        if data:
            save_history(code, data)
            success += 1
        else:
            failed += 1

        time.sleep(random.uniform(0.05, 0.15))

    logger.info(f"完成: 成功 {success}, 失败 {failed}")
    return {'success': success, 'failed': failed, 'total': len(codes)}

def get_history_from_file(code):
    history_file = os.path.join(DATA_DIR, f'{code}.json')
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        code = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 365
        data = generate_fund_history(code, days)
        if data:
            save_history(code, data)
            print(f"已生成 {code} 历史数据: {data['days']} 条")
        else:
            print(f"生成 {code} 历史数据失败")
    else:
        import argparse
        parser = argparse.ArgumentParser(description='生成基金历史数据')
        parser.add_argument('--incremental', action='store_true', help='增量更新（只更新最新一天）')
        parser.add_argument('--days', type=int, default=365, help='全量生成时的天数（默认365）')
        args = parser.parse_args()
        
        if args.incremental:
            logger.info(f"开始增量更新历史数据")
            result = generate_all_history(days=args.days, incremental=True)
        else:
            logger.info(f"开始全量生成历史数据 (默认{args.days}天)")
            result = generate_all_history(days=args.days, incremental=False)
        
        print(f"\n完成! 成功: {result['success']}, 失败: {result['failed']}, 总计: {result['total']}")
        print(f"历史数据目录: {DATA_DIR}")