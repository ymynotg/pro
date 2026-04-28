#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 深市LOF数据更新脚本
# 数据来源：searchapi.eastmoney.com (与深交所数据同步)
import logging
import os
import json
import shutil
import configparser
from datetime import datetime
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'update_lof_szse.log')
CONFIG_FILE = os.path.join(BASE_DIR, 'lof_config.json')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
LOG_CONF_FILE = os.path.join(BASE_DIR, 'config', 'logging.conf')

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

def setup_logger(name='update_lof_szse'):
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

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'funds': [], 'update_time': ''}

def backup_config(logger):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BACKUP_DIR, f'lof_config_{timestamp}.json')
        shutil.copy2(CONFIG_FILE, backup_file)
        logger.info(f"配置已备份到: {backup_file}")
        return backup_file
    return None

def fetch_latest_lof_szse(logger):
    """从东方财富searchapi获取最新深市LOF数据"""
    import requests
    
    logger.info("开始获取最新深市LOF数据")
    logger.info("数据源: searchapi.eastmoney.com")
    
    session = requests.Session()
    all_lofs = {}
    keywords = ['LOF', 'lof']
    
    url = 'https://searchapi.eastmoney.com/api/suggest/get'
    
    try:
        for kw in keywords:
            params = {'input': kw, 'type': '14', 'count': '200'}
            logger.debug(f"调用接口: {url}, keyword={kw}")
            r = session.get(url, params=params, timeout=15)
            data = r.json()
            
            items = data.get('QuotationCodeTable', {}).get('Data') or []
            for item in items:
                code = item.get('Code', '')
                name = item.get('Name', '')
                if code.isdigit() and len(code) == 6 and code.startswith('1'):
                    if code not in all_lofs:
                        all_lofs[code] = name
        
        result = []
        for code, name in sorted(all_lofs.items(), key=lambda x: int(x[0])):
            result.append({
                'code': code,
                'name': name,
                'type': 'SZLOF',
                'source': 'searchapi.eastmoney.com',
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        logger.info(f"获取成功, 共 {len(result)} 只深市LOF (SZLOF)")
        return result
        
    except Exception as e:
        logger.warning(f"获取失败: {str(e)}")
        return None

def merge_data(old_data, new_data, logger):
    """合并数据：保留SHLOF，更新SZLOF"""
    # 保留非SZLOF（SHLOF等）
    non_sz = [f for f in old_data if f.get('type') != 'SZLOF']
    merged = non_sz + new_data
    
    # 统计新增
    old_sz_codes = {f['code'] for f in old_data if f.get('type') == 'SZLOF'}
    new_count = sum(1 for f in new_data if f['code'] not in old_sz_codes)
    
    logger.info(f"合并完成: 沪市SHLOF={len(non_sz)}, 深市SZLOF={len(new_data)}, 新增={new_count}, 总计={len(merged)}")
    return merged

def save_config(data, logger):
    config = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(data),
        'funds': data
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"配置已保存到 {CONFIG_FILE}")

def main():
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("深市LOF数据更新脚本启动")
    logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
    
    # 备份
    backup_config(logger)
    
    # 加载历史
    old_config = load_config()
    old_data = old_config.get('funds', [])
    logger.info(f"已加载历史配置: {len(old_data)} 只基金")
    
    # 获取新数据
    new_data = fetch_latest_lof_szse(logger)
    if not new_data:
        logger.error("获取数据失败")
        return
    
    # 合并保存
    merged = merge_data(old_data, new_data, logger)
    save_config(merged, logger)
    
    logger.info("更新完成!")

if __name__ == '__main__':
    main()