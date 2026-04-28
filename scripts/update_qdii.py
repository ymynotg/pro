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
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'update_qdii.log')
CONFIG_FILE = os.path.join(BASE_DIR, 'qdii_config.json')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
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

def setup_logger(name='update_qdii'):
    level = load_log_level()
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
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

def load_current_config(logger):
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"配置文件不存在: {CONFIG_FILE}")
        return None
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"已加载配置文件, 当前 {config.get('count', 0)} 只QDII基金")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        return None

def backup_config(logger):
    if not os.path.exists(CONFIG_FILE):
        return False
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BACKUP_DIR, f'qdii_config_{timestamp}.json')
        shutil.copy2(CONFIG_FILE, backup_file)
        
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('qdii_config_')])
        while len(backups) > 10:
            oldest = backups.pop(0)
            os.remove(os.path.join(BACKUP_DIR, oldest))
        
        logger.info(f"配置已备份到 {backup_file}")
        return True
    except Exception as e:
        logger.error(f"备份失败: {str(e)}")
        return False

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

def merge_funds(old_funds, new_funds, logger):
    existing_codes = {f['code'] for f in old_funds}
    
    added = [f for f in new_funds if f['code'] not in existing_codes]
    removed = [f for f in old_funds if f['code'] not in {f['code'] for f in new_funds}]
    kept = [f for f in new_funds if f['code'] in existing_codes]
    
    if added:
        logger.info(f"新增基金: {len(added)} 只 - {[f['code'] for f in added[:5]]}")
    if removed:
        logger.info(f"移除基金: {len(removed)} 只 - {[f['code'] for f in removed[:5]]}")
    
    result = new_funds
    logger.info(f"合并完成: 共 {len(result)} 只QDII基金")
    return result

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
    logger.info("QDII数据更新脚本启动")
    logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
    
    old_config = load_current_config(logger)
    old_funds = old_config.get('funds', []) if old_config else []
    
    backup_config(logger)
    
    data = None
    
    sources = [
        ('rankhandler', fetch_qdii_rankhandler),
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
        if old_funds:
            data = merge_funds(old_funds, data, logger)
        
        save_config(data, logger)
        logger.info(f"完成! 共获取 {len(data)} 只QDII基金")
    else:
        logger.error("所有数据源均失败, 保留原配置")
        if old_funds:
            logger.info(f"保留原配置: {len(old_funds)} 只QDII基金")

if __name__ == '__main__':
    main()