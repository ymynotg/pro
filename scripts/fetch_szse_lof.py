#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深市LOF基金数据获取脚本
=======================
整合szse_lof_list.py和fetch_lof_szse.py的功能
从深圳证券交易所或东方财富获取所有LOF基金列表

数据源:
    1. 深圳证券交易所: https://www.szse.cn/api/report/ShowReport/data
    2. 东方财富searchapi: https://searchapi.eastmoney.com/api/suggest/get

功能:
    - 获取所有深市LOF基金列表（代码、名称、管理人）
    - 生成配置文件到config目录
    - 追加写入，代码存在不追加
    - 完整的日志记录
    - 多数据源fallback机制

配置文件格式(config/szse_lof_config.json):
    [
        {
            "序号": 1,
            "代码": "161039",
            "名称": "易方达消费行业股票(LOF)",
            "管理人": "易方达基金管理有限公司",
            "类型": "股票型",
            "更新时间": "2024-01-01 12:00:00"
        },
        ...
    ]
"""

import sys
import os
import json
import re
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
LOG_FILE = os.path.join(LOG_DIR, 'fetch_szse_lof.log')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'szse_lof_config.json')
LOG_CONF_FILE = os.path.join(CONFIG_DIR, 'logging.conf')

# API配置
API_URL = 'https://www.szse.cn/api/report/ShowReport/data'
SEARCH_API_URL = 'https://searchapi.eastmoney.com/api/suggest/get'


def fetch_from_searchapi(logger):
    """
    从东方财富搜索API获取深市LOF数据（备用数据源）
    返回的数据不包含管理人信息
    
    Returns:
        list: [{'code': str, 'name': str, 'manager': str, 'fund_type': str}, ...]
        None: 获取失败时返回
    """
    logger.info("尝试从东方财富searchapi获取数据（备用数据源）")
    
    session = requests.Session()
    all_lofs = {}
    keywords = ['LOF', 'lof']
    
    try:
        for kw in keywords:
            params = {'input': kw, 'type': '14', 'count': '200'}
            logger.debug(f"调用searchapi: keyword={kw}")
            
            # 添加随机延迟避免被限流
            time.sleep(random.uniform(0.5, 1.5))
            
            r = session.get(SEARCH_API_URL, params=params, timeout=15)
            data = r.json()
            
            items = data.get('QuotationCodeTable', {}).get('Data') or []
            for item in items:
                code = item.get('Code', '')
                name = item.get('Name', '')
                # 1xx开头对应深市LOF
                if code.isdigit() and len(code) == 6 and code.startswith('1'):
                    if code not in all_lofs:
                        all_lofs[code] = name
        
        result = []
        for code, name in sorted(all_lofs.items(), key=lambda x: int(x[0])):
            result.append({
                'code': code,
                'name': name,
                'manager': '',
                'fund_type': '',
            })
        
        logger.info(f"searchapi获取成功, 共 {len(result)} 只深市LOF")
        return result if result else None
        
    except Exception as e:
        logger.warning(f"searchapi获取失败: {str(e)}")
        return None


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


def setup_logger(name='fetch_szse_lof'):
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
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件日志 - 轮转日志，最大10MB，保留5个备份
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 控制台日志 - 仅INFO级别
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


def get_lof_list_page(page=1, page_size=50):
    """
    获取LOF基金列表（单页）
    
    Args:
        page: 页码，默认1
        page_size: 每页数量，默认50
    
    Returns:
        dict: {
            'total': int,      # 总数
            'page': int,       # 当前页
            'page_size': int,  # 每页数量
            'page_count': int, # 总页数
            'funds': list      # 基金列表
        }
        None: 获取失败时返回
    """
    params = {
        'SHOWTYPE': 'JSON',
        'CATALOGID': '1945_LOF',
        'loading': 'first' if page == 1 else 'normal',
        'page': page,
        'pageSize': page_size,
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.szse.cn/market/product/list/lofFundList/index.html',
    }
    
    try:
        logger = logging.getLogger('fetch_szse_lof')
        logger.debug(f"调用深交所API: page={page}, pageSize={page_size}")
        
        resp = requests.get(API_URL, params=params, headers=headers, timeout=30)
        data = resp.json()
        logger.debug(f"手动定位信息:API_URL={API_URL};params={params};headers={headers};data={data}")
        if not data or not data[0].get('metadata'):
            logger.warning(f"API返回数据格式异常: {data}")
            return None
        
        meta = data[0]['metadata']
        records = data[0].get('data', [])
        
        funds = []
        for r in records:
            # 提取代码 - 从sys_key字段中提取
            code_match = re.search(r'>([0-9]+)<', r.get('sys_key', ''))
            code = code_match.group(1) if code_match else ''
            
            # 提取名称 - 从kzjcurl字段中提取
            name_match = re.search(r'<u>([^<]+)</u>', r.get('kzjcurl', ''))
            name = name_match.group(1) if name_match else ''
            
            if code and name:
                funds.append({
                    'code': code,
                    'name': name,
                    'scale': r.get('dqgm', ''),           # 规模(万份)
                    'manager': r.get('glrmc', ''),         # 管理人
                    'fund_type': r.get('jjlx', ''),        # 基金类型
                    'index': r.get('nhzs', '').strip(),    # 拟合指数
                })
        
        logger.debug(f"第{page}页获取成功: {len(funds)}条记录")
        
        return {
            'total': meta.get('recordcount', 0),
            'page': meta.get('pageno', page),
            'page_size': page_size,
            'page_count': meta.get('pagecount', 0),
            'funds': funds,
        }
        
    except requests.exceptions.Timeout:
        logger = logging.getLogger('fetch_szse_lof')
        logger.warning(f"API请求超时: page={page}")
    except requests.exceptions.RequestException as e:
        logger = logging.getLogger('fetch_szse_lof')
        logger.warning(f"API请求失败: {str(e)}")
    except Exception as e:
        logger = logging.getLogger('fetch_szse_lof')
        logger.warning(f"获取数据异常: {str(e)}")
    
    return None


def get_all_lof_list(logger):
    """
    获取所有深市LOF基金列表
    
    优先使用深交所API，失败时使用东方财富searchapi作为备用
    
    Args:
        logger: 日志记录器
    
    Returns:
        list: [{'code': str, 'name': str, 'manager': str, 'fund_type': str}, ...]
        None: 获取失败时返回
    """
    logger.info("开始获取深市LOF基金列表")
    logger.info(f"主数据源: {API_URL}")
    
    all_funds = []
    seen_codes = set()  # 用于去重
    page = 1
    page_size = 10  # 深交所API只支持每页10条
    
    while True:
        result = get_lof_list_page(page, page_size)
        
        if not result or not result.get('funds'):
            logger.warning(f"第{page}页获取失败或无数据")
            break
        
        # 去重处理
        new_count = 0
        for fund in result['funds']:
            if fund['code'] not in seen_codes:
                all_funds.append(fund)
                seen_codes.add(fund['code'])
                new_count += 1
        
        logger.info(f"已获取第 {page} 页 ({len(result['funds'])} 条, 新增{new_count}条), 总计 {len(all_funds)}/{result['total']}")
        
        # 判断是否还有下一页
        if page >= result.get('page_count', 1):
            break
        page += 1
    
    # 如果深交所API获取数据过少，尝试备用数据源
    if len(all_funds) < 50:
        logger.warning(f"深交所API获取数据过少({len(all_funds)}条)，尝试备用数据源")
        backup_data = fetch_from_searchapi(logger)
        if backup_data:
            # 合并备用数据
            for fund in backup_data:
                if fund['code'] not in seen_codes:
                    all_funds.append(fund)
                    seen_codes.add(fund['code'])
            logger.info(f"备用数据源获取完成, 当前总计 {len(all_funds)} 只")
    
    if all_funds:
        logger.info(f"获取完成, 共 {len(all_funds)} 只深市LOF基金")
    else:
        logger.warning("未能获取任何LOF基金数据")
    
    return all_funds if all_funds else None


def load_existing_config(logger):
    """
    加载现有配置文件
    
    Args:
        logger: 日志记录器
    
    Returns:
        list: 已存在的基金列表
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"已加载现有配置: {len(data)} 只基金")
                return data
        except json.JSONDecodeError as e:
            logger.warning(f"配置文件JSON解析失败: {str(e)}")
        except Exception as e:
            logger.warning(f"加载配置文件失败: {str(e)}")
    
    logger.info("配置文件不存在，将创建新文件")
    return []


def merge_data(existing_data, new_data, logger):
    """
    合并新旧数据，保留已存在的记录，新数据追加
    
    Args:
        existing_data: 已存在的基金列表
        new_data: 新获取的基金列表（格式：{'代码': xxx, ...}）
        logger: 日志记录器
    
    Returns:
        list: 合并后的基金列表
    """
    # 构建现有代码集合
    existing_codes = {fund['代码'] for fund in existing_data if '代码' in fund}
    logger.info(f"现有基金代码数量: {len(existing_codes)}")
    
    # 过滤掉已存在的代码（使用'代码'字段）
    new_funds = [f for f in new_data if f['代码'] not in existing_codes]
    logger.info(f"新增基金数量: {len(new_funds)}")
    
    # 合并数据
    merged = existing_data + new_funds
    
    # 按代码排序
    merged.sort(key=lambda x: x.get('代码', ''))
    
    # 重新生成序号
    for i, fund in enumerate(merged, 1):
        fund['序号'] = i
    
    logger.info(f"合并完成, 总计 {len(merged)} 只基金")
    
    return merged


def save_config(data, logger):
    """
    保存配置文件
    
    Args:
        data: 基金列表数据
        logger: 日志记录器
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"配置已保存到 {CONFIG_FILE}, 共 {len(data)} 只基金")


def main():
    """主函数"""
    # 初始化日志记录器
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("深市LOF数据获取脚本启动")
    logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
    
    # 获取数据
    new_data = get_all_lof_list(logger)
    
    if not new_data:
        logger.error("获取数据失败，程序退出")
        return
    
    # 获取当前时间
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 转换数据格式
    formatted_data = []
    for fund in new_data:
        formatted_data.append({
            '序号': 0,  # 将在merge_data中重新编号
            '代码': fund['code'],
            '名称': fund['name'],
            '管理人': fund.get('manager', ''),
            '类型': fund.get('fund_type', ''),
            '更新时间': update_time
        })
    
    # 加载并合并现有数据
    existing_data = load_existing_config(logger)
    
    # 合并数据（追加新数据，保留已有数据）
    merged_data = merge_data(existing_data, formatted_data, logger)
    
    # 保存配置
    save_config(merged_data, logger)
    
    logger.info("=" * 60)
    logger.info("深市LOF数据获取脚本完成")
    logger.info(f"新增: {len(formatted_data)}, 总计: {len(merged_data)}")


if __name__ == '__main__':
    main()
