#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOF基金数据生成脚本
===================
从input目录下的Excel文件读取数据，生成配置文件到config目录

功能:
    - 读取Excel文件获取LOF基金列表
    - 生成配置文件到config目录
    - 追加写入，代码存在不追加
    - 完整的日志记录
    - 支持深市/沪市LOF

使用方式:
    python3 fetch_excel_lof.py              # 默认处理深市LOF
    python3 fetch_excel_lof.py szse         # 处理深市LOF
    python3 fetch_excel_lof.py sse          # 处理沪市LOF
    python3 fetch_excel_lof.py all          # 处理全部

输入文件:
    - input/szse_lof.xlsx  (深市LOF)
    - input/sse_lof.xlsx   (沪市LOF)

配置文件格式:
    [
        {
            "序号": 1,
            "代码": "161039",
            "名称": "易方达消费行业股票(LOF)",
            "管理人": "易方达基金管理有限公司",
            "类型": "场内/场外/QDII",
            "拟合指数": "000932 中证消费",
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
from datetime import datetime
from logging.handlers import RotatingFileHandler
import pandas as pd

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
INPUT_DIR = os.path.join(BASE_DIR, 'input')
LOG_CONF_FILE = os.path.join(CONFIG_DIR, 'logging.conf')


def classify_fund_type(name):
    """
    分类基金类型（场内、场外、QDII）
    
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
               '日经', '欧洲', '德国', '越南']
    
    # 场外关键词（有封闭期的LOF）
    outside_kw = ['定开', '定期开放', 'FOF', '封闭']
    
    if any(kw in name for kw in qdii_kw):
        return 'QDII'
    elif any(kw in name for kw in outside_kw):
        return '场外'
    else:
        return '场内'


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


def setup_logger(name='fetch_excel_lof'):
    """配置日志记录器"""
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
        os.path.join(LOG_DIR, f'{name}.log'), 
        maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
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


def read_excel_file(file_path, logger):
    """
    读取Excel文件获取LOF数据
    
    Args:
        file_path: Excel文件路径
        logger: 日志记录器
    
    Returns:
        list: [{'code': str, 'name': str, 'manager': str, 'index': str}, ...]
        None: 读取失败时返回
    """
    logger.info(f"开始读取Excel文件: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"Excel文件不存在: {file_path}")
        return None
    
    try:
        df = pd.read_excel(file_path)
        logger.info(f"成功读取Excel, 共 {len(df)} 条记录")
        logger.debug(f"列名: {df.columns.tolist()}")
        
        funds = []
        for _, row in df.iterrows():
            # 兼容深市和沪市Excel的不同列名
            code = str(row.get('证券代码', row.get('基金代码', ''))).strip()
            name = str(row.get('证券简称', row.get('基金扩位简称', ''))).strip()
            manager = str(row.get('基金管理人', '')).strip()
            index = str(row.get('拟合指数', '')).strip()
            
            if code and name:
                funds.append({
                    'code': code,
                    'name': name,
                    'manager': manager,
                    'index': index,
                })
        
        logger.info(f"解析完成, 共 {len(funds)} 只LOF基金")
        return funds
        
    except Exception as e:
        logger.error(f"读取Excel文件失败: {str(e)}")
        return None


def load_existing_config(file_path, logger):
    """加载现有配置文件"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"已加载现有配置: {len(data)} 只基金")
                return data
        except Exception as e:
            logger.warning(f"加载配置文件失败: {str(e)}")
    
    logger.info("配置文件不存在，将创建新文件")
    return []


def merge_data(existing_data, new_data, logger):
    """合并新旧数据，保留已存在的记录，新数据追加"""
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


def save_config(data, file_path, logger):
    """保存配置文件"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"配置已保存到 {file_path}, 共 {len(data)} 只基金")


def process_lof(target, logger):
    """
    处理LOF数据
    
    Args:
        target: 'szse' 深市, 'sse' 沪市, 'all' 全部
        logger: 日志记录器
    """
    # 根据目标设置文件路径
    targets_config = {
        'szse': {
            'input': os.path.join(INPUT_DIR, 'szse_lof.xlsx'),
            'output': os.path.join(CONFIG_DIR, 'szse_lof_config.json'),
            'name': '深市LOF'
        },
        'sse': {
            'input': os.path.join(INPUT_DIR, 'sse_lof.xlsx'),
            'output': os.path.join(CONFIG_DIR, 'sse_lof_config.json'),
            'name': '沪市LOF'
        }
    }
    
    if target not in targets_config:
        logger.error(f"未知目标: {target}")
        return
    
    config = targets_config[target]
    
    # 读取Excel数据
    raw_data = read_excel_file(config['input'], logger)
    
    if not raw_data:
        logger.error("读取数据失败，程序退出")
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
            '管理人': fund['manager'],
            '类型': fund_type,
            '拟合指数': fund['index'],
            '更新时间': update_time
        })
    
    logger.info(f"数据格式化完成, 共 {len(formatted_data)} 条")
    
    # 加载并合并现有数据
    existing_data = load_existing_config(config['output'], logger)
    merged_data = merge_data(existing_data, formatted_data, logger)
    
    # 保存配置
    save_config(merged_data, config['output'], logger)
    
    # 统计类型
    from collections import Counter
    types = Counter(f['类型'] for f in merged_data)
    logger.info(f"类型统计: {dict(types)}")
    
    return len(formatted_data), len(merged_data)


def main():
    """主函数"""
    # 获取命令行参数
    target = sys.argv[1].lower() if len(sys.argv) > 1 else 'szse'
    
    logger = setup_logger('fetch_excel_lof')
    
    if target == 'all':
        # 处理全部
        logger.info("=" * 60)
        logger.info("LOF数据生成脚本启动（处理全部）")
        logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
        
        total_new = 0
        total_all = 0
        
        for t in ['szse', 'sse']:
            logger.info("-" * 40)
            result = process_lof(t, logger)
            if result:
                total_new += result[0]
                total_all += result[1]
        
        logger.info("=" * 60)
        logger.info(f"全部处理完成: 新增{total_new}, 总计{total_all}")
        
    else:
        # 处理单个目标
        target_name = '深市' if target == 'szse' else '沪市'
        
        logger.info("=" * 60)
        logger.info(f"{target_name}LOF数据生成脚本启动")
        logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
        
        result = process_lof(target, logger)
        
        if result:
            logger.info("=" * 60)
            logger.info(f"{target_name}LOF数据生成脚本完成")
            logger.info(f"新增: {result[0]}, 总计: {result[1]}")


if __name__ == '__main__':
    main()