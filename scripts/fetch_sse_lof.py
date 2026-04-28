#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海LOF基金数据获取脚本
=======================
从东方财富获取上海证券交易所所有LOF基金列表

数据源: https://fund.eastmoney.com/data/rankhandler.aspx

功能:
    - 获取所有上海LOF基金列表
    - 生成配置文件到config目录
    - 追加写入，代码存在不追加
    - 完整的日志记录
    - 基金类型分类（场内、场外、QDII、其他）

配置文件格式(config/sse_lof_config.json):
    [
        {
            "序号": 1,
            "代码": "501001",
            "名称": "财通多策略精选混合(LOF)",
            "管理人": "",
            "类型": "场内",
            "拟合指数": "",
            "更新时间": "2024-01-01 12:00:00"
        },
        ...
    ]
"""

import sys
import os
import json
import logging
import configparser
import time
import random
from datetime import datetime
from logging.handlers import RotatingFileHandler
import requests

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
LOG_FILE = os.path.join(LOG_DIR, 'fetch_sse_lof.log')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'sse_lof_config.json')
LOG_CONF_FILE = os.path.join(CONFIG_DIR, 'logging.conf')


def load_log_level():
    """从配置文件加载日志级别"""
    if os.path.exists(LOG_CONF_FILE):
        try:
            config = configparser.ConfigParser()
            config.read(LOG_CONF_FILE)
            if 'log' in config and 'level' in config['log']:
                level_str = config['log']['level'].strip().upper()
                return getattr(logging, level_str, logging.DEBUG)
        except Exception:
            pass
    return logging.DEBUG


def setup_logger(name='fetch_sse_lof'):
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
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
    except Exception:
        pass
    
    return logger


def classify_fund_type(name):
    """
    分类基金类型（场内、场外、QDII、其他）
    
    Args:
        name: 基金名称
    
    Returns:
        str: 基金类型
    """
    # QDII关键词
    qdii_kw = ['QDII', '香港', '纳斯达克', '标普', '全球', '美国', 'REIT', 
               '油气', '能源', '印度', '原油', '黄金', '海外', '中概', '港股',
               '标普500', '标普医疗', '标普生物', '标普信息', '纳斯达克100',
               '美国REIT', '全球油气', '印度基金', '南方香港', '恒生', 'H股',
               '日经', '欧洲', '德国', '法国', '东南亚']
    
    # 场外关键词（有封闭期的LOF）
    outside_kw = ['定开', '定期开放', 'FOF', '封闭','(LOF)C']
    
    if any(kw in name for kw in qdii_kw):
        return 'QDII'
    elif any(kw in name for kw in outside_kw):
        return '场外'
    else:
        return '场内'


def fetch_sse_lof(logger):
    """
    从东方财富获取上交所LOF数据
    
    Args:
        logger: 日志记录器
    
    Returns:
        list: [{'code': str, 'name': str}, ...]
        None: 获取失败时返回
    """
    logger.info("开始获取上海LOF基金列表")
    logger.info("数据源: https://fund.eastmoney.com/data/rankhandler.aspx")
    
    url = 'https://fund.eastmoney.com/data/rankhandler.aspx'
    params = {
        'op': 'ph',
        'dt': 'kf',
        'ft': 'all',
        'pi': 1,
        'pn': 5000,
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://fund.eastmoney.com/data/fundranking.html',
    }
    
    try:
        # 添加随机延迟
        time.sleep(random.uniform(1, 3))
        
        logger.debug(f"调用接口: GET {url}")
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        
        if resp.status_code != 200:
            logger.warning(f"rankhandler返回状态码: {resp.status_code}")
            return None
        
        text = resp.text
        if 'ErrCode' in text or '无访问权限' in text:
            logger.warning(f"东方财富接口返回无访问权限")
            return None
        
        # 解析数据
        start = text.find('datas:"[') + 7
        end = text.find('"]', start)
        records = text[start:end].split('","')
        
        sh_lofs = {}
        for rec in records:
            parts = rec.split(',')
            if len(parts) >= 2:
                code = parts[0]
                name = parts[1]
                # 5xx开头是上交所LOF
                if code.isdigit() and len(code) == 6 and code.startswith('5'):
                    if code not in sh_lofs:
                        sh_lofs[code] = name
        
        result = []
        for code, name in sorted(sh_lofs.items(), key=lambda x: int(x[0])):
            result.append({
                'code': code,
                'name': name,
            })
        
        logger.info(f"获取成功, 共 {len(result)} 只上海LOF")
        return result if result else None
        
    except Exception as e:
        logger.warning(f"获取失败: {str(e)}")
        return None


def load_existing_config(logger):
    """加载现有配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"已加载现有配置: {len(data)} 只基金")
                return data
        except Exception as e:
            logger.warning(f"加载配置文件失败: {str(e)}")
    
    logger.info("配置文件不存在，将创建新文件")
    return []


def merge_data(existing_data, new_data, logger):
    """
    合并新旧数据，保留已存在的记录，新数据追加
    """
    existing_codes = {fund['代码'] for fund in existing_data if '代码' in fund}
    logger.info(f"现有基金代码数量: {len(existing_codes)}")
    
    new_funds = [f for f in new_data if f['代码'] not in existing_codes]
    logger.info(f"新增基金数量: {len(new_funds)}")
    
    merged = existing_data + new_funds
    merged.sort(key=lambda x: x.get('代码', ''))
    
    for i, fund in enumerate(merged, 1):
        fund['序号'] = i
    
    logger.info(f"合并完成, 总计 {len(merged)} 只基金")
    
    return merged


def save_config(data, logger):
    """保存配置文件"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"配置已保存到 {CONFIG_FILE}, 共 {len(data)} 只基金")


def main():
    """主函数"""
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("上海LOF数据获取脚本启动")
    logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
    
    # 获取数据
    raw_data = fetch_sse_lof(logger)
    
    if not raw_data:
        logger.error("获取数据失败，程序退出")
        return
    
    # 获取当前时间
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 转换数据格式
    formatted_data = []
    for fund in raw_data:
        fund_type = classify_fund_type(fund['name'])
        
        formatted_data.append({
            '序号': 0,
            '代码': fund['code'],
            '名称': fund['name'],
            '管理人': '',
            '类型': fund_type,
            '拟合指数': '',
            '更新时间': update_time
        })
    
    # 加载并合并现有数据
    existing_data = load_existing_config(logger)
    merged_data = merge_data(existing_data, formatted_data, logger)
    
    # 保存配置
    save_config(merged_data, logger)
    
    logger.info("=" * 60)
    logger.info("上海LOF数据获取脚本完成")
    logger.info(f"新增: {len(formatted_data)}, 总计: {len(merged_data)}")


if __name__ == '__main__':
    main()