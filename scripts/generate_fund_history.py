#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金历史数据生成脚本
====================
从腾讯 K 线接口获取历史价格，从东方财富 API 获取历史净值，
合并计算出每日溢价率，保存到 fund_history/{code}.json。

用法:
    python3 generate_fund_history.py                      # 全量生成所有基金
    python3 generate_fund_history.py --incremental        # 增量更新所有基金
    python3 generate_fund_history.py 160105               # 生成单只基金（默认365天）
    python3 generate_fund_history.py 160105 --days 7      # 生成单只基金最近7天
    python3 generate_fund_history.py --lof-only           # 只处理LOF基金
"""
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

# ---------- 路径常量 ----------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))          # 项目根目录
LOG_DIR = os.path.join(BASE_DIR, 'logs')                       # 日志目录
LOG_FILE = os.path.join(LOG_DIR, 'generate_history.log')       # 日志文件路径
DATA_DIR = os.path.join(BASE_DIR, 'fund_history')              # 历史数据存储目录
LOF_CONFIG = os.path.join(BASE_DIR, 'lof_config.json')         # LOF基金配置文件
QDII_CONFIG = os.path.join(BASE_DIR, 'qdii_config.json')       # QDII基金配置文件
LOG_CONF_FILE = os.path.join(BASE_DIR, 'config', 'logging.conf')  # 日志级别配置文件


def load_log_level():
    """从 config/logging.conf 读取日志级别，不存在则返回 INFO"""
    if os.path.exists(LOG_CONF_FILE):
        try:
            config = configparser.ConfigParser()
            config.read(LOG_CONF_FILE)
            if 'log' in config and 'level' in config['log']:
                return getattr(logging, config['log']['level'].strip().upper(), logging.INFO)
        except Exception:
            pass
    return logging.INFO


def setup_logger(name='generate_history'):
    """
    配置日志记录器：
    - 日志文件按大小轮转，最大 10MB，保留 5 个备份
    - 日志格式: 时间 - 级别 - 消息
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(load_log_level())
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh = RotatingFileHandler(
            LOG_FILE, maxBytes=10*1024*1024,
            backupCount=5, encoding='utf-8'
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger


logger = setup_logger()


def get_tencent_kline(code, days=365):
    """
    从腾讯行情接口获取复权 K 线数据（日收盘价）
    接口: web.ifzq.gtimg.cn
    参数:
        code: 基金代码（6位数字）
        days: 获取天数
    返回:
        {日期(yyyy-mm-dd): 收盘价(float)} 字典
    """
    # 深市代码以 1 开头，沪市代码以 5 开头
    market = 'sz' if code.startswith('1') else 'sh'
    url = (
        f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/'
        f'get?_var=kline_day&param={market}{code},day,,,{days},qfq'
    )
    logger.info(f"{code}: 开始获取腾讯K线数据，天数={days}")
    try:
        resp = requests.get(
            url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10
        )
        # 响应格式: var kline_day={...}，提取 JSON 部分
        match = re.search(r'kline_day\s*=\s*({.+})', resp.text)
        if match:
            data = json.loads(match.group(1))
            code_data = data.get('data', {}).get(f'{market}{code}', {})
            # 优先使用复权数据 qfqday，回退到 day
            klines = code_data.get('qfqday', []) or code_data.get('day', [])
            result = {
                item[0]: float(item[2])
                for item in klines
                if len(item) >= 3 and float(item[2]) > 0
            }
            logger.info(f"{code}: 腾讯K线获取成功，共 {len(result)} 条")
            return result
        else:
            logger.warning(f"{code}: 腾讯K线响应中未找到 kline_day 数据")
    except Exception as e:
        logger.warning(f"{code}: 腾讯K线获取失败 - {e}")
    return {}


def get_historical_nav(code, days=365):
    """
    从东方财富 API 获取基金历史净值（分页拉取全部数据）
    接口: api.fund.eastmoney.com/f10/lsjz
    返回:
        {日期(yyyy-mm-dd): 单位净值(float)} 字典
    """
    url = 'https://api.fund.eastmoney.com/f10/lsjz'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://fund.eastmoney.com/',
    }
    nav_dict = {}
    page_index = 1
    max_pages = 500  # 安全限制：最多获取500页（约10000条）

    logger.info(f"{code}: 开始获取历史净值")
    try:
        while page_index <= max_pages:
            params = {
                'fundCode': code,
                'pageIndex': page_index,
                'pageSize': 20,   # API 每次最多返回 20 条
                'startDate': '',
                'endDate': '',
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('Data') and data['Data'].get('LSJZList'):
                    lsjz_list = data['Data']['LSJZList']
                    if not lsjz_list:
                        break  # 无更多数据
                    for item in lsjz_list:
                        date = item.get('FSRQ', '')    # 日期
                        nav = item.get('DWJZ', '')     # 单位净值
                        if date and nav:
                            nav_dict[date] = float(nav)
                    # API 不足 20 条表示已到最后一页
                    if len(lsjz_list) < 20:
                        break
                    page_index += 1
                    time.sleep(0.1)  # 控制请求频率，避免被封
                else:
                    break
            else:
                logger.warning(
                    f"{code}: 历史净值API返回状态码 {resp.status_code}"
                )
                break

        logger.info(f"{code}: 历史净值获取完成，共 {len(nav_dict)} 条")
        return nav_dict
    except Exception as e:
        logger.warning(f"{code}: 历史净值获取失败 - {e}")
        return {}


def get_fund_realtime(code):
    """
    从天天基金接口获取基金实时估值
    接口: fundgz.1234567.com.cn
    返回:
        {nav: 最新净值, valuation: 实时估值, change: 涨跌幅} 
        或 None（获取失败时）
    """
    url = f'https://fundgz.1234567.com.cn/js/{code}.js'
    try:
        resp = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://fund.eastmoney.com/'
        }, timeout=10)
        # 响应格式: jsonpgz({...});
        if 'jsonpgz' in resp.text and resp.text != 'jsonpgz();':
            match = re.search(r'jsonpgz\((.+)\)', resp.text)
            if match:
                data = json.loads(match.group(1))
                result = {
                    'nav': float(data.get('dwjz', 0)),       # 最新单位净值
                    'valuation': float(data.get('gsz', 0)),  # 盘中实时估值
                    'change': float(data.get('gszzl', 0)),   # 估值涨跌幅(%)
                }
                logger.debug(f"{code}: 实时估值获取成功")
                return result
    except Exception:
        pass
    logger.debug(f"{code}: 实时估值获取失败")
    return None


def generate_fund_history(code, days=365):
    """
    全量生成单只基金的历史数据
    流程:
        1. 从腾讯接口获取每日收盘价
        2. 从东方财富接口获取每日单位净值
        3. 计算每日涨跌幅和溢价率
        4. 按日期降序排列

    参数:
        code: 基金代码
        days: 获取的天数范围
    返回:
        {code, days, update_time, history: [...]} 或 None
    """
    logger.info(f"{code}: 开始全量生成历史数据（天数={days}）")

    # 步骤1: 获取历史收盘价
    price_map = get_tencent_kline(code, days)
    if not price_map:
        logger.warning(f"{code}: 未获取到价格数据，跳过")
        return None

    # 步骤2: 获取历史单位净值
    nav_map = get_historical_nav(code, days)
    if not nav_map:
        logger.warning(f"{code}: 无法获取历史净值，暂停生成")
        return None

    # 步骤3: 获取实时估值（用于估值列）
    realtime = get_fund_realtime(code)
    valuation = realtime.get('valuation', 0) if realtime else 0

    # 步骤4: 按日期降序合并，计算涨跌幅和溢价率
    dates = sorted(price_map.keys(), reverse=True)[:days]
    history = []

    for i, date in enumerate(dates):
        price = price_map[date]                    # 当日收盘价
        nav = nav_map.get(date, 0)                 # 当日单位净值

        # 溢价率 = (价格 - 净值) / 净值 * 100
        premium = ((price - nav) / nav * 100) if nav > 0 and price > 0 else 0

        # 涨跌幅 = 相对于前一交易日（dates 中后一个）的变化
        if i < len(dates) - 1:
            prev_price = price_map[dates[i + 1]]
            change = round((price - prev_price) / prev_price * 100, 2)
        else:
            change = 0

        history.append({
            'date': date,
            'nav': round(nav, 4) if nav > 0 else '',
            'valuation': round(valuation, 4) if valuation > 0 else '',
            'price': round(price, 4),
            'change': change,
            'premium': round(premium, 2) if premium else '',
        })

    result = {
        'code': code,
        'days': len(history),
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'history': history
    }

    logger.info(f"{code}: 全量生成完成，共 {len(history)} 条数据")
    return result


def save_history(code, data):
    """将基金历史数据写入 fund_history/{code}.json"""
    history_file = os.path.join(DATA_DIR, f'{code}.json')
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"{code}: 数据已保存到 {history_file}")


def load_fund_codes(lof_only=False):
    """
    从配置文件中加载所有基金代码
    参数:
        lof_only: True 只加载 LOF 基金，False 同时加载 LOF + QDII
    返回:
        去重后的基金代码列表
    """
    codes = []

    # 加载 LOF 基金配置
    if os.path.exists(LOF_CONFIG):
        with open(LOF_CONFIG, 'r', encoding='utf-8') as f:
            config = json.load(f)
            for fund in config.get('funds', []):
                codes.append(fund.get('code'))
        logger.info(f"从 {LOF_CONFIG} 加载了 LOF 基金配置")

    # 加载 QDII 基金配置
    if not lof_only and os.path.exists(QDII_CONFIG):
        with open(QDII_CONFIG, 'r', encoding='utf-8') as f:
            config = json.load(f)
            for fund in config.get('funds', []):
                codes.append(fund.get('code'))
        logger.info(f"从 {QDII_CONFIG} 加载了 QDII 基金配置")

    return list(set(codes))


def update_fund_history(code, days=365, incremental=True):
    """
    Update single fund historical data (incremental or full rebuild).

    Incremental mode:
        - Read existing fund_history/{code}.json
        - Fetch latest 5 days of price + NAV
        - For each date: if exists, update fields in-place; if not, insert new record
        - Recalculate change% for affected entries

    Full mode:
        - Re-fetch all data from APIs
        - Overwrite file

    Args:
        code: Fund code (6-digit string)
        days: Number of days for full generation
        incremental: True for incremental update, False for full rebuild
    Returns:
        Data dict on success, None on failure
    """
    history_file = os.path.join(DATA_DIR, f'{code}.json')
    logger.info(f"{code}: 开始{'增量更新' if incremental else '全量更新'}")

    if incremental and os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            logger.info(f"{code}: 读取现有数据，共 {old_data['days']} 条")

            # Fetch latest 5 days of price, NAV and realtime valuation
            INCREMENTAL_DAYS = 5
            price_map = get_tencent_kline(code, INCREMENTAL_DAYS)
            if not price_map:
                logger.warning(f"{code}: 增量更新未获取到新价格数据")
                return None

            nav_map = get_historical_nav(code, INCREMENTAL_DAYS)
            realtime = get_fund_realtime(code)
            valuation = realtime.get('valuation', 0) if realtime else 0

            history = old_data['history']
            new_dates = sorted(price_map.keys(), reverse=True)
            max_touched = -1

            for date in new_dates:
                price = price_map.get(date, 0)
                nav = nav_map.get(date, 0)
                premium = round((price - nav) / nav * 100, 2) if nav > 0 and price > 0 else ''

                existing_idx = next((i for i, r in enumerate(history) if r['date'] == date), None)

                if existing_idx is not None:
                    history[existing_idx].update({
                        'nav': round(nav, 4) if nav > 0 else '',
                        'valuation': round(valuation, 4) if valuation > 0 else '',
                        'price': round(price, 4),
                        'premium': premium,
                    })
                    max_touched = max(max_touched, existing_idx)
                    logger.info(f"{code}: {date} 已更新 (price={price}, nav={nav}, premium={premium}%)")
                else:
                    insert_idx = next((i for i, r in enumerate(history) if r['date'] < date), len(history))
                    history.insert(insert_idx, {
                        'date': date,
                        'nav': round(nav, 4) if nav > 0 else '',
                        'valuation': round(valuation, 4) if valuation > 0 else '',
                        'price': round(price, 4),
                        'change': 0,
                        'premium': premium,
                    })
                    max_touched = max(max_touched, insert_idx)
                    logger.info(f"{code}: {date} 新增 (price={price}, nav={nav}, premium={premium}%)")

            # Recalculate change for affected entries (0 to max_touched + 1)
            recalc_end = min(max_touched + 2, len(history))
            for i in range(recalc_end):
                if i < len(history) - 1:
                    prev_price = history[i + 1]['price']
                    curr_price = history[i]['price']
                    if prev_price > 0 and curr_price > 0:
                        history[i]['change'] = round((curr_price - prev_price) / prev_price * 100, 2)
                    else:
                        history[i]['change'] = 0
                else:
                    history[i]['change'] = 0

            old_data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            old_data['days'] = len(history)
            logger.info(f"{code}: 增量更新完成，共 {old_data['days']} 条")
            return old_data

        except Exception as e:
            logger.warning(f"{code}: 增量更新失败({e})，降级为全量生成")

    # 全量生成模式（或增量降级）
    return generate_fund_history(code, days)


def generate_all_history(days=365, incremental=False, lof_only=False):
    """
    批量生成/更新所有基金的历史数据
    遍历基金列表，逐个调用 update_fund_history，每处理一只间隔 1-3 秒

    参数:
        days: 全量生成时的天数
        incremental: True 增量更新，False 全量替换
        lof_only: True 只处理 LOF 基金
    返回:
        {success, failed, total}
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    codes = load_fund_codes(lof_only=lof_only)
    logger.info(
        f"开始{'增量更新' if incremental else '全量生成'}历史数据，"
        f"共 {len(codes)} 只基金"
    )

    success = 0
    failed = 0

    for i, code in enumerate(codes):
        logger.info(f"[{i+1}/{len(codes)}] 正在处理基金 {code}")
        data = update_fund_history(code, days, incremental)

        if data:
            save_history(code, data)
            success += 1
        else:
            logger.error(f"{code}: 处理失败")
            failed += 1

        # 请求间隔，避免触发 API 频率限制
        time.sleep(random.uniform(1, 3))

    logger.info(f"批量处理完成: 成功 {success}, 失败 {failed}, 总计 {len(codes)}")
    return {'success': success, 'failed': failed, 'total': len(codes)}


def get_history_from_file(code):
    """从本地文件读取基金历史数据，文件不存在则返回 None"""
    history_file = os.path.join(DATA_DIR, f'{code}.json')
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


if __name__ == '__main__':
    # ---------- 命令行参数解析 ----------
    import argparse
    parser = argparse.ArgumentParser(
        description='基金历史数据生成工具',
        epilog=(
            '示例:\n'
            '  python3 generate_fund_history.py                        全量生成所有基金\n'
            '  python3 generate_fund_history.py --incremental          增量更新所有基金\n'
            '  python3 generate_fund_history.py 160105                 单只基金(默认365天)\n'
            '  python3 generate_fund_history.py 160105 --days 7       单只基金最近7天\n'
            '  python3 generate_fund_history.py --lof-only            只处理LOF基金\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('code', nargs='?', help='单个基金代码（可选，不传则处理全部）')
    parser.add_argument('--days', type=int, default=365, help='全量生成时的天数（默认365）')
    parser.add_argument('--incremental', action='store_true', help='增量更新（只追加最新一天数据）')
    parser.add_argument('--lof-only', action='store_true', help='只处理LOF基金，跳过QDII')
    args = parser.parse_args()

    logger.info(
        f"脚本启动 | 参数: code={args.code}, days={args.days}, "
        f"incremental={args.incremental}, lof_only={args.lof_only}"
    )

    if args.code:
        # 单只基金模式
        logger.info(f"单只基金模式: {args.code}, 天数={args.days}")
        data = generate_fund_history(args.code, args.days)
        if data:
            save_history(args.code, data)
            print(f"已生成 {args.code} 历史数据: {data['days']} 条")
        else:
            print(f"生成 {args.code} 历史数据失败")
    else:
        # 批量模式
        if args.incremental:
            logger.info("批量增量更新模式")
            result = generate_all_history(
                days=args.days, incremental=True, lof_only=args.lof_only
            )
        else:
            mode = 'LOF' if args.lof_only else '全部'
            logger.info(f"批量全量生成模式: {mode}")
            result = generate_all_history(
                days=args.days, incremental=False, lof_only=args.lof_only
            )

        print(
            f"\n完成! 成功: {result['success']}, "
            f"失败: {result['failed']}, 总计: {result['total']}"
        )
        print(f"历史数据目录: {DATA_DIR}")
