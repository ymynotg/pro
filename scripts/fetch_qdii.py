#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import json
import configparser
from datetime import datetime
from logging.handlers import RotatingFileHandler
import requests
import time
import random

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'fetch_qdii.log')
CONFIG_FILE = os.path.join(BASE_DIR, 'qdii_config.json')
LOG_CONF_FILE = os.path.join(BASE_DIR, 'config', 'logging.conf')

def classify_fund_type(name):
    name_upper = name.upper()
    if 'LOF' in name_upper or ('QDII-LOF' in name_upper):
        return 'QDII_LOF'
    else:
        return 'QDII'

def load_log_level():
    if os.path.exists(LOG_CONF_FILE):
        try:
            config = configparser.ConfigParser()
            config.read(LOG_CONF_FILE)
            if 'log' in config and 'level' in config['log']:
                level_str = config['log']['level'].strip().upper()
                return getattr(logging, level_str, logging.DEBUG)
        except:
            pass
    return logging.DEBUG

def setup_logger(name='fetch_qdii'):
    level = load_log_level()
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    try:
        config = configparser.ConfigParser()
        config.read(LOG_CONF_FILE)
        if config.getboolean('log', 'console', fallback=True):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
    except:
        pass
    
    return logger

def fetch_qdii_rankhandler(logger):
    logger.info("尝试使用东方财富rankhandler获取QDII数据")
    
    url = 'https://fund.eastmoney.com/data/rankhandler.aspx'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://fund.eastmoney.com/data/fundranking.html',
    }
    
    params = {
        'op': 'ph',
        'dt': 'kf',
        'ft': 'qdii',
        'pi': 1,
        'pn': 5000,
    }
    
    try:
        time.sleep(random.uniform(1, 3))
        session = requests.Session()
        session.headers.update(headers)
        
        logger.debug(f"调用接口: POST {url}, ft=qdii")
        resp = session.post(url, params=params, timeout=30)
        
        if resp.status_code != 200:
            logger.warning(f"rankhandler返回状态码: {resp.status_code}")
            return None
        
        text = resp.text
        start = text.find('datas:"[') + 7
        end = text.find('"]', start)
        records = text[start:end].split('","')
        
        qdiis = []
        for rec in records:
            parts = rec.split(',')
            if len(parts) >= 2:
                code = parts[0]
                name = parts[1]
                if code.isdigit() and len(code) == 6:
                    fund_type = classify_fund_type(name)
                    qdiis.append({
                        'code': code,
                        'name': name,
                        'type': fund_type,
                        'source': 'eastmoney/rankhandler',
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        logger.info(f"东方财富rankhandler获取成功, 共 {len(qdiis)} 只QDII基金")
        return qdiis
        
    except Exception as e:
        logger.warning(f"东方财富rankhandler调用失败: {str(e)}")
        return None

def fetch_qdii_searchapi(logger):
    logger.info("尝试使用东方财富搜索API获取QDII数据")
    session = requests.Session()
    
    all_funds = {}
    keywords = ['QDII', 'qdii', '全球', '美国', '港股', '日本', '欧洲', '印度', '越南']
    
    url = 'https://searchapi.eastmoney.com/api/suggest/get'
    
    try:
        for kw in keywords:
            params = {'input': kw, 'type': '14', 'count': '100'}
            logger.debug(f"调用接口: {url}, keyword={kw}")
            r = session.get(url, params=params, timeout=15)
            data = r.json()
            
            items = data.get('QuotationCodeTable', {}).get('Data') or []
            for item in items:
                code = item.get('Code', '')
                name = item.get('Name', '')
                if code.isdigit() and len(code) == 6:
                    if code not in all_funds:
                        all_funds[code] = name
        
        result = []
        for code, name in sorted(all_funds.items(), key=lambda x: int(x[0])):
            result.append({
                'code': code,
                'name': name,
                'type': 'QDII',
                'source': 'eastmoney/searchapi',
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        logger.info(f"东方财富搜索API获取成功, 共 {len(result)} 只QDII相关基金")
        return result
        
    except Exception as e:
        logger.warning(f"东方财富搜索API调用失败: {str(e)}")
        return None

def fetch_qdii_fallback(logger):
    logger.info("使用备用QDII代码列表数据")
    
    QDII_FUNDS = [
        ('460005', '华安国际龙头ETF'),
        ('460288', '华安黄金ETF'),
        ('470008', '嘉实美国消费ETF'),
        ('47088', '嘉实美国消费'),
        ('378006', '易方达标普500ETF'),
        ('378008', '易方达标普科技ETF'),
        ('460058', '华安纳斯达克100ETF'),
        ('460188', '华安德国30ETF'),
        ('470041', '嘉实沪深300ETF'),
        ('470031', '嘉实中证500ETF'),
        ('470101', '嘉实中证全指证券公司ETF'),
        ('460031', '华安中证全指证券公司ETF'),
        ('161130', '易方达科创板50ETF'),
        ('161039', '易方达消费行业ETF'),
        ('460001', '华安上证50ETF'),
        ('160725', '招商丰庆灵活配置'),
        ('163406', '兴全合宜混合'),
        ('166002', '中欧创新成长混合'),
        ('161017', '富国天惠成长混合'),
        ('160215', '嘉实原油主题股票'),
    ]
    
    data = []
    for code, name in QDII_FUNDS:
        data.append({
            'code': code,
            'name': name,
            'type': 'QDII',
            'source': 'fallback',
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    logger.info(f"备用数据: 共 {len(data)} 只QDII基金")
    return data

def save_config(data, logger):
    config = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(data),
        'funds': data
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"配置已保存到 {CONFIG_FILE}, 共 {len(data)} 只基金")

def main():
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("QDII数据获取脚本启动")
    logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
    
    data = None
    
    sources = [
        ('rankhandler', fetch_qdii_rankhandler),
        ('searchapi', fetch_qdii_searchapi),
        ('fallback', fetch_qdii_fallback),
    ]
    
    for source_name, fetch_func in sources:
        logger.info(f"尝试数据源: {source_name}")
        result = fetch_func(logger)
        
        if result:
            data = result
            logger.info(f"数据源 {source_name} 成功获取数据")
            break
        else:
            logger.warning(f"数据源 {source_name} 获取失败, 尝试下一个")
    
    if data:
        save_config(data, logger)
        logger.info(f"完成! 共获取 {len(data)} 只QDII基金")
    else:
        logger.error("所有数据源均失败")
        data = fetch_qdii_fallback(logger)
        save_config(data, logger)
        logger.info(f"使用备用数据完成, 共 {len(data)} 只QDII基金")

if __name__ == '__main__':
    main()
