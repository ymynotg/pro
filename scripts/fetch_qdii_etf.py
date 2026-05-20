#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QDII ETF数据获取脚本
===================
从Tushare获取A股市场上所有QDII ETF基金列表

数据源:
    Tushare Pro API - fund_basic接口
    
功能:
    - 获取所有ETF基金基础信息
    - 筛选出QDII类型的ETF
    - 生成配置文件到config目录
    - 完整的日志记录
    - 支持多数据源fallback

API接口说明:
    1. fund_basic: 获取基金基础信息
       - 接口: https://tushare.pro/document/2?doc_id=25
       - 字段: ts_code(基金代码), name(基金名称), management(管理人), 
              fund_type(基金类型), invest_type(投资类型), issue_date(发行日期)
    
    2. fund_share: 获取基金规模信息(可选)
       - 接口: https://tushare.pro/document/2?doc_id=26
       - 字段: ts_code, total_share(总份额)

配置文件格式(config/qdii_etf_config.json):
    [
        {
            "序号": 1,
            "代码": "513100",
            "名称": "纳指ETF",
            "管理人": "国泰基金管理有限公司",
            "类型": "QDII-ETF",
            "拟合指数": "NDX",
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

# 尝试导入tushare
try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    print("警告: tushare未安装,请执行: pip install tushare")

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
LOG_FILE = os.path.join(LOG_DIR, 'fetch_qdii_etf.log')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'qdii_etf_config.json')
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


def setup_logger(name='fetch_qdii_etf'):
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


def init_tushare(logger):
    """
    初始化Tushare Pro API
    
    Args:
        logger: 日志记录器
    
    Returns:
        tushare.pro_api: Tushare Pro API对象
        None: 初始化失败时返回
    """
    if not TUSHARE_AVAILABLE:
        logger.error("tushare未安装,无法使用Tushare数据源")
        return None
    
    # 尝试从环境变量获取token
    token = os.environ.get('TUSHARE_TOKEN')
    
    if not token:
        # 尝试从配置文件读取
        tushare_conf = os.path.join(CONFIG_DIR, 'tushare.conf')
        if os.path.exists(tushare_conf):
            try:
                config = configparser.ConfigParser()
                config.read(tushare_conf)
                token = config.get('tushare', 'token', fallback=None)
            except Exception:
                pass
    
    if not token:
        logger.error("未找到TUSHARE_TOKEN,请设置环境变量或配置文件")
        logger.info("设置方法: export TUSHARE_TOKEN=your_token")
        return None
    
    try:
        logger.info(f"初始化Tushare Pro API, token前缀: {token[:8]}...")
        pro = ts.pro_api(token)
        # 测试接口是否可用
        logger.debug("测试Tushare接口连接...")
        test_data = pro.trade_cal(exchange='SSE', start_date='20240101', end_date='20240101')
        if test_data is not None:
            logger.info("Tushare接口连接成功")
            return pro
        else:
            logger.warning("Tushare接口测试失败")
            return None
    except Exception as e:
        logger.error(f"Tushare初始化失败: {str(e)}")
        return None


def fetch_etf_from_tushare(logger):
    """
    从Tushare获取ETF基金列表
    
    调用API接口:
        fund_basic - 获取基金基础信息
        文档: https://tushare.pro/document/2?doc_id=25
        
    获取字段:
        ts_code: 基金代码 (如: 513100.SH)
        name: 基金名称
        management: 管理人
        fund_type: 基金类型 (ETF基金)
        invest_type: 投资类型
        issue_date: 发行日期
        list_date: 上市日期
        market: 交易市场 (E: 场内)
        
    Args:
        logger: 日志记录器
    
    Returns:
        list: [{'code': str, 'name': str, 'manager': str, 'fund_type': str}, ...]
        None: 获取失败时返回
    """
    logger.info("开始从Tushare获取ETF基金列表")
    
    pro = init_tushare(logger)
    if not pro:
        return None
    
    try:
        # 调用fund_basic接口获取所有ETF基金
        logger.info("调用Tushare API: fund_basic, market='E' (场内基金)")
        logger.debug("API文档: https://tushare.pro/document/2?doc_id=25")
        
        # 获取场内基金(ETF)
        df = pro.fund_basic(market='E')
        
        if df is None or df.empty:
            logger.warning("fund_basic返回空数据")
            return None
        
        logger.info(f"获取到 {len(df)} 只场内基金")
        
        # 筛选ETF基金
        # fund_type字段包含'ETF'的为ETF基金
        etf_df = df[df['fund_type'].str.contains('ETF', case=False, na=False)]
        logger.info(f"筛选出 {len(etf_df)} 只ETF基金")
        
        # 转换为列表格式
        result = []
        for _, row in etf_df.iterrows():
            # 提取代码(去掉后缀 .SH/.SZ)
            ts_code = row['ts_code']
            code = ts_code.split('.')[0]
            
            result.append({
                'code': code,
                'name': row['name'],
                'manager': row.get('management', ''),
                'fund_type': row.get('fund_type', ''),
                'invest_type': row.get('invest_type', ''),
                'issue_date': row.get('issue_date', ''),
                'list_date': row.get('list_date', ''),
            })
        
        logger.info(f"Tushare获取成功, 共 {len(result)} 只ETF基金")
        return result
        
    except Exception as e:
        logger.error(f"Tushare获取失败: {str(e)}")
        return None


def identify_qdii_etf(etf_list, logger):
    """
    从ETF列表中识别QDII ETF
    
    识别规则:
        1. 名称中包含QDII相关关键词: QDII, 港股, 美股, 纳指, 标普, 恒生, 
           德国, 日本, 法国, 英国, 欧洲, 印度, 越南, 韩国, 澳洲, 黄金, 原油, 油气
        2. 投资类型为'QDII'
        3. 代码特征: 51xxxx(上交所), 15xxxx(深交所)
    
    Args:
        etf_list: ETF基金列表
        logger: 日志记录器
    
    Returns:
        list: QDII ETF列表
    """
    logger.info("开始识别QDII ETF")
    
    # QDII相关关键词
    qdii_keywords = [
        'QDII', 'qdii',
        '港股', 'HK', '恒生', 'H股',
        '美股', 'US', '纳指', '纳斯达克', '标普', '道琼斯',
        '德国', 'DAX', '法国', 'CAC', '英国', '富时', '欧洲', 'EU',
        '日本', '日经', '韩国', 'KOSPI',
        '印度', '越南', '澳洲', '澳大利亚',
        '黄金', 'Gold', '原油', 'Oil', '油气', '能源',
        '全球', '国际', '海外', '跨境',
    ]
    
    qdii_etfs = []
    
    for etf in etf_list:
        name = etf['name']
        invest_type = etf.get('invest_type', '')
        
        # 判断是否为QDII ETF
        is_qdii = False
        match_reason = []
        
        # 方法1: 检查投资类型
        if 'QDII' in invest_type.upper():
            is_qdii = True
            match_reason.append(f"投资类型={invest_type}")
        
        # 方法2: 检查名称关键词
        for keyword in qdii_keywords:
            if keyword.lower() in name.lower():
                is_qdii = True
                match_reason.append(f"名称包含'{keyword}'")
                break
        
        if is_qdii:
            etf['is_qdii'] = True
            etf['match_reason'] = '; '.join(match_reason)
            qdii_etfs.append(etf)
    
    logger.info(f"识别出 {len(qdii_etfs)} 只QDII ETF")
    
    # 输出识别结果示例
    if qdii_etfs:
        logger.info("QDII ETF识别示例:")
        for i, etf in enumerate(qdii_etfs[:5], 1):
            logger.info(f"  {i}. {etf['code']} {etf['name']} - {etf.get('match_reason', '')}")
    
    return qdii_etfs


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
        new_data: 新获取的基金列表
        logger: 日志记录器
    
    Returns:
        list: 合并后的基金列表
    """
    # 构建现有代码集合
    existing_codes = {fund['代码'] for fund in existing_data if '代码' in fund}
    logger.info(f"现有基金代码数量: {len(existing_codes)}")
    
    # 过滤掉已存在的代码
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


def fetch_qdii_etf_from_eastmoney(logger):
    """
    从东方财富获取QDII ETF列表(备用数据源)
    
    调用API接口:
        东方财富基金列表API
        URL: https://fund.eastmoney.com/data/rankhandler.aspx
        
    获取字段:
        基金代码, 基金名称, 基金类型等
        
    Args:
        logger: 日志记录器
    
    Returns:
        list: QDII ETF列表
        None: 获取失败时返回
    """
    import requests
    import time
    import random
    
    logger.info("尝试从东方财富获取QDII ETF数据(备用数据源)")
    
    url = 'https://fund.eastmoney.com/data/rankhandler.aspx'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://fund.eastmoney.com/data/fundranking.html',
    }
    
    # ETF基金类型参数
    params = {
        'op': 'ph',
        'dt': 'kf',
        'ft': 'etf',  # 改为etf
        'rs': '',
        'gs': '0',
        'sc': 'zzf',
        'st': 'desc',
        'qdii': '',
        'pi': 1,
        'pn': 5000,
    }
    
    try:
        time.sleep(random.uniform(1, 3))
        session = requests.Session()
        session.headers.update(headers)
        
        logger.debug(f"调用东方财富API: {url}, ft=etf")
        resp = session.post(url, params=params, timeout=30)
        
        if resp.status_code != 200:
            logger.warning(f"东方财富API返回状态码: {resp.status_code}")
            return None
        
        # 解析返回数据
        text = resp.text
        start = text.find('datas:"[') + 7
        end = text.find('"]', start)
        records = text[start:end].split('","')
        
        logger.debug(f"东方财富返回ETF记录数: {len(records)}")
        
        # QDII相关关键词
        qdii_keywords = [
            'QDII', 'qdii',
            '港股', 'HK', '恒生', 'H股',
            '美股', 'US', '纳指', '纳斯达克', '标普', '道琼斯',
            '德国', 'DAX', '法国', 'CAC', '英国', '富时', '欧洲', 'EU',
            '日本', '日经', '韩国', 'KOSPI',
            '印度', '越南', '澳洲', '澳大利亚',
            '黄金', 'Gold', '原油', 'Oil', '油气', '能源',
            '全球', '国际', '海外', '跨境',
        ]
        
        qdii_etfs = []
        sample_count = 0
        for rec in records:
            parts = rec.split(',')
            if len(parts) >= 20:
                code = parts[0]
                name = parts[1]
                
                # 输出前10条记录用于调试
                if sample_count < 10:
                    logger.debug(f"示例ETF记录: code={code}, name={name}")
                    sample_count += 1
                
                # 筛选QDII ETF(通过名称判断)
                if code.isdigit() and len(code) == 6:
                    name_upper = name.upper()
                    # 判断是否为QDII类型
                    for keyword in qdii_keywords:
                        if keyword.lower() in name.lower():
                            qdii_etfs.append({
                                'code': code,
                                'name': name,
                                'manager': parts[14] if len(parts) > 14 else '',
                                'fund_type': 'ETF',
                                'invest_type': 'QDII',
                            })
                            break
        
        logger.info(f"东方财富获取成功, 共 {len(qdii_etfs)} 只QDII ETF")
        return qdii_etfs
        
    except Exception as e:
        logger.warning(f"东方财富API调用失败: {str(e)}")
        return None


def main():
    """主函数"""
    # 初始化日志记录器
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("QDII ETF数据获取脚本启动")
    logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
    
    # 尝试多种数据源
    etf_list = None
    data_source = None
    
    # 数据源1: Tushare (优先)
    if TUSHARE_AVAILABLE:
        logger.info("尝试数据源1: Tushare Pro API")
        etf_list = fetch_etf_from_tushare(logger)
        if etf_list:
            data_source = 'Tushare'
    
    # 数据源2: 东方财富 (备用)
    if not etf_list:
        logger.info("尝试数据源2: 东方财富API")
        etf_list = fetch_qdii_etf_from_eastmoney(logger)
        if etf_list:
            data_source = 'EastMoney'
    
    if not etf_list:
        logger.error("所有数据源均失败，程序退出")
        logger.info("请检查:")
        logger.info("  1. Tushare token是否配置正确")
        logger.info("  2. 网络连接是否正常")
        logger.info("  3. 参考 config/tushare.conf.example 配置Tushare token")
        return
    
    logger.info(f"使用数据源: {data_source}")
    
    # 识别QDII ETF (如果是从Tushare获取的,需要进一步筛选)
    if data_source == 'Tushare':
        qdii_etfs = identify_qdii_etf(etf_list, logger)
    else:
        # 东方财富已经筛选过QDII ETF
        qdii_etfs = etf_list
    
    if not qdii_etfs:
        logger.warning("未识别到任何QDII ETF")
        return
    
    # 获取当前时间
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 转换数据格式
    formatted_data = []
    for etf in qdii_etfs:
        formatted_data.append({
            '序号': 0,  # 将在merge_data中重新编号
            '代码': etf['code'],
            '名称': etf['name'],
            '管理人': etf.get('manager', ''),
            '类型': 'QDII-ETF',
            '拟合指数': '',  # 可以后续补充
            '更新时间': update_time
        })
    
    # 加载并合并现有数据
    existing_data = load_existing_config(logger)
    
    # 合并数据（追加新数据，保留已有数据）
    merged_data = merge_data(existing_data, formatted_data, logger)
    
    # 保存配置
    save_config(merged_data, logger)
    
    logger.info("=" * 60)
    logger.info("QDII ETF数据获取脚本完成")
    logger.info(f"新增: {len(formatted_data)}, 总计: {len(merged_data)}")
    
    # 输出API调用总结
    logger.info("\n" + "=" * 60)
    logger.info("API调用总结:")
    if data_source == 'Tushare':
        logger.info("数据源: Tushare Pro API")
        logger.info("1. fund_basic接口")
        logger.info("   接口文档: https://tushare.pro/document/2?doc_id=25")
        logger.info("   获取字段: ts_code, name, management, fund_type, invest_type, issue_date, list_date")
        logger.info("   筛选条件: market='E' (场内基金), fund_type包含'ETF'")
    else:
        logger.info("数据源: 东方财富API")
        logger.info("1. rankhandler接口")
        logger.info("   URL: https://fund.eastmoney.com/data/rankhandler.aspx")
        logger.info("   参数: op=ph, dt=kf, ft=qdii")
        logger.info("   筛选条件: 代码51xxxx或15xxxx, 名称包含ETF")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
