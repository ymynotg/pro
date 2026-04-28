#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import json
import shutil
import configparser
from datetime import datetime
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'update_lof_shanghai.log')
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

def setup_logger(name='update_lof_shanghai'):
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

def fetch_latest_lof_akshare(logger):
    import akshare as ak
    
    logger.info("尝试使用akshare获取最新LOF数据")
    try:
        logger.debug("调用接口: akshare.fund_lof_spot_em()")
        df = ak.fund_lof_spot_em()
        logger.info(f"akshare.fund_lof_spot_em() 调用成功, 获取 {len(df)} 条记录")
        
        data = []
        for _, row in df.iterrows():
            code = str(row.get('代码', ''))
            if code:
                data.append({
                    'code': code,
                    'name': str(row.get('名称', '')),
                    'type': 'SHLOF',
                    'source': 'akshare.fund_lof_spot_em()',
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        logger.info(f"数据处理完成, 共 {len(data)} 只LOF基金")
        return data
        
    except Exception as e:
        logger.warning(f"akshare接口调用失败: {str(e)}")
        return None

def fetch_latest_lof_eastmoney(logger):
    import requests
    
    logger.info("尝试使用东方财富接口获取最新LOF��据")
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://fund.eastmoney.com/data/lof.html'
    })
    
    url = 'https://fund.eastmoney.com/data/rankhandler.aspx'
    params = {
        'ft': '4',
        'pi': '1',
        'pn': '5000',
        'dtt': '4'
    }
    
    try:
        logger.debug(f"调用接口: GET {url}")
        r = session.get(url, params=params, timeout=30)
        logger.info(f"东方财富接口返回: status={r.status_code}, length={len(r.text)}")
        
        text = r.text
        if 'ErrCode' in text or '无访问权限' in text:
            logger.warning(f"东方财富接口返回无访问权限")
            return None
        
        if text and 'rankData' in text:
            import re
            match = re.search(r'var rankData = ({.*?});', text)
            if match:
                import json as json_module
                data_json = match.group(1)
                data_obj = json_module.loads(data_json)
                
                if 'datas' in data_obj and data_obj['datas']:
                    logger.info(f"获取到 {len(data_obj['datas'])} 条记录")
                    
                    data = []
                    for item in data_obj['datas']:
                        parts = item.split(',')
                        if len(parts) >= 2:
                            data.append({
                                'code': parts[0],
                                'name': parts[1],
                                'type': 'SHLOF',
                                'source': 'eastmoney/rankhandler',
                                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                    logger.info(f"数据处理完成, 共 {len(data)} 只LOF基金")
                    return data
        
        logger.warning(f"东方财富返回数据格式异常")
        return None
        
    except Exception as e:
        logger.warning(f"东方财富接口调用失败: {str(e)}")
        return None

def merge_data(old_data, new_data, logger):
    old_codes = {f['code'] for f in old_data}
    merged = old_data.copy()
    new_count = 0
    
    for fund in new_data:
        if fund['code'] not in old_codes:
            merged.append(fund)
            new_count += 1
            logger.info(f"新增基金: {fund['code']} - {fund['name']}")
    
    logger.info(f"数据合并完成: 原有 {len(old_data)} 只, 新增 {new_count} 只, 共 {len(merged)} 只")
    return merged

def save_updated_config(merged_data, logger):
    config = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(merged_data),
        'funds': merged_data
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"配置已更新并保存到 {CONFIG_FILE}, 共 {len(merged_data)} 只基金")

def main():
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("LOF数据更新脚本启动")
    logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
    
    backup_config(logger)
    
    old_config = load_config()
    old_data = old_config.get('funds', [])
    logger.info(f"已加载历史配置: {len(old_data)} 只基金")
    
    data = None
    
    sources = [
        ('akshare', fetch_latest_lof_akshare),
        ('eastmoney', fetch_latest_lof_eastmoney),
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
    
    if not data:
        logger.warning("所有在线数据源均失败, 使用现有数据")
        data = old_data
    
    merged = merge_data(old_data, data, logger)
    save_updated_config(merged, logger)
    logger.info("更新完成!")

if __name__ == '__main__':
    main()