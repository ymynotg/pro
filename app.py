#!/usr/bin/env python3
# 跨境套利系统后端
# 安装依赖: pip install -r requirements.txt
# 运行: python3 app.py

import os
import sys
import json
import requests
import time
import random
import logging
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
import datetime
import threading
import re

# 配置日志
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

logger = logging.getLogger('arbitrage_system')
logger.setLevel(logging.DEBUG)

# 文件处理器：轮转日志，最大10MB，保留5个备份
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# 控制台处理器：只显示INFO及以上级别
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# 缓存配置
CACHE = {}                    # 市场数据缓存(场内价格/估值)
CACHE_EXPIRE = 300            # 市场数据缓存有效期(秒), 5分钟
NAV_CACHE = {}                # 净值缓存(实时净值)
NAV_CACHE_EXPIRE = 28800      # 净值缓存有效期(秒), 8小时
STATUS_CACHE = {}             # 申购/赎回/限额状态缓存
STATUS_CACHE_EXPIRE = 28800   # 状态缓存有效期(秒), 8小时
HISTORY_CACHE = {}            # 历史数据内存缓存
HISTORY_LOCK = threading.Lock() # 历史缓存线程锁

# 并发控制: 20个工作线程
EXECUTOR = ThreadPoolExecutor(max_workers=20)

app = Flask(__name__, template_folder='.')
CORS(app)

# 路径配置
BASE_DIR = os.path.dirname(__file__)
LOF_CONFIG = os.path.join(BASE_DIR, 'lof_config.json')
QDII_CONFIG = os.path.join(BASE_DIR, 'qdii_config.json')
FUND_HISTORY_DIR = os.path.join(BASE_DIR, 'fund_history')

# 并发控制: 20个工作线程
EXECUTOR = ThreadPoolExecutor(max_workers=20)

def load_config(config_file):
    """
    加载JSON配置文件
    
    Args:
        config_file: 配置文件路径
    
    Returns:
        dict: 配置数据, 失败返回None
    """
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return None

def get_fund_realtime(code):
    """
    从天天基金获取基金实时数据(估值、净值)
    
    Args:
        code: 基金代码
    
    Returns:
        dict: 包含price/valuation/nav/change/update_time, 失败返回None
    """
    import datetime
    url = f'https://fundgz.1234567.com.cn/js/{code}.js?rt={int(datetime.datetime.now().timestamp())}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://fund.eastmoney.com/',
    }
    
    start_time = time.time()
    logger.debug(f"[REQUEST] 天天基金实时数据 - URL: {url}")
    logger.debug(f"[REQUEST] Headers: {headers}")
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        elapsed = round((time.time() - start_time) * 1000, 2)
        
        logger.debug(f"[RESPONSE] 状态码: {resp.status_code}, 耗时: {elapsed}ms")
        logger.debug(f"[RESPONSE] 内容长度: {len(resp.text)} 字符")
        
        if resp.status_code == 200:
            text = resp.text
            logger.debug(f"[RESPONSE] 返回内容前100字符: {text[:100]}")
            
            if 'jsonpgz' in text:
                import re
                match = re.search(r'jsonpgz\(({.+})\)', text)
                if match:
                    data = json.loads(match.group(1))
                    result = {
                        'price': float(data.get('gsz', 0)),       # 估算价格
                        'nav': float(data.get('dwjz', 0)),        # 单位净值
                        'valuation': float(data.get('gsz', 0)),     # 估值(同估算价格)
                        'change': float(data.get('gszzl', 0)),   # 涨跌幅(%) - 修复字段名
                        'update_time': data.get('gztime', ''),   # 更新时间
                    }
                    logger.info(f"[SUCCESS] 基金{code} - 净值:{result['nav']}, 估算:{result['price']}, 涨跌:{result['change']}%")
                    return result
            else:
                logger.warning(f"[WARNING] 基金{code} - 返回内容不包含jsonpgz")
        else:
            logger.error(f"[ERROR] 基金{code} - HTTP状态码: {resp.status_code}")
            
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[ERROR] 基金{code} - 请求失败: {str(e)}, 耗时: {elapsed}ms")
        
    return None

def get_market_price(code):
    """
    从腾讯行情获取LOF基金实时交易价格
    
    Args:
        code: 基金代码, 以1开头为深市, 5开头为沪市
    
    Returns:
        dict: 包含price和change_percent字段, 获取失败返回{'price': 0, 'change_percent': 0}
    """
    import re
    market = 'sz' if code.startswith('1') else 'sh'
    url = f'https://qt.gtimg.cn/q={market}{code}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    start_time = time.time()
    logger.debug(f"[REQUEST] 腾讯行情接口 - URL: {url}")
    logger.debug(f"[REQUEST] 交易所: {market}, 基金代码: {code}")
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        elapsed = round((time.time() - start_time) * 1000, 2)
        
        logger.debug(f"[RESPONSE] 状态码: {resp.status_code}, 耗时: {elapsed}ms")
        logger.debug(f"[RESPONSE] 内容长度: {len(resp.text)} 字符")
        
        if resp.status_code == 200:
            content = resp.text
            logger.debug(f"[RESPONSE] 返回内容前100字符: {content[:100]}")
            
            # 解析腾讯实时行情数据, 格式: v_sz162411="1~基金名称~代码~当前价~昨收~今开~..."
            # 使用非贪婪匹配避免多个引号问题
            match = re.search(r'v_\w+="([^"]+)"', content)
            if match:
                fields = match.group(1).split('~')
                logger.debug(f"[PARSE] 解析到 {len(fields)} 个字段")
                
                if len(fields) > 32:
                    current_price = float(fields[3]) if fields[3] else 0
                    change_percent = float(fields[32]) if fields[32] else 0
                    logger.info(f"[SUCCESS] 基金{code} - 当前价:{current_price}, 涨跌幅:{change_percent}%")
                    return {'price': current_price if current_price > 0 else 0, 'change_percent': change_percent}
                else:
                    logger.warning(f"[WARNING] 基金{code} - 字段数量不足: {len(fields)}")
            else:
                logger.warning(f"[WARNING] 基金{code} - 正则匹配失败")
        else:
            logger.error(f"[ERROR] 基金{code} - HTTP状态码: {resp.status_code}")
            
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[ERROR] 基金{code} - 请求失败: {str(e)}, 耗时: {elapsed}ms")
        
    return {'price': 0, 'change_percent': 0}

def fetch_fund_data(code):
    """
    获取单只基金完整数据(带缓存)
    净值缓存8小时, 场内价格/估值缓存300秒
    
    Args:
        code: 基金代码
    
    Returns:
        dict: 包含realtime/market_price/time
    """
    cache_key = f'fund_{code}'
    nav_cache_key = f'nav_{code}'
    now = time.time()
    
    nav_cached = nav_cache_key in NAV_CACHE and now - NAV_CACHE[nav_cache_key].get('time', 0) < NAV_CACHE_EXPIRE
    market_cached = cache_key in CACHE and now - CACHE[cache_key].get('time', 0) < CACHE_EXPIRE
    
    if nav_cached and market_cached:
        nav_entry = NAV_CACHE[nav_cache_key]
        market_entry = CACHE[cache_key]
        realtime = {
            'nav': nav_entry.get('nav', 0),
            'valuation': market_entry.get('valuation', 0),
            'change': market_entry.get('change', ''),
            'update_time': nav_entry.get('update_time', ''),
        }
        return {
            'realtime': realtime,
            'market_price': market_entry.get('market_price', {}),
            'time': now
        }
    
    realtime = get_fund_realtime(code)
    market_price_data = get_market_price(code)
    
    if realtime:
        NAV_CACHE[nav_cache_key] = {
            'nav': realtime.get('nav', 0),
            'update_time': realtime.get('update_time', ''),
            'time': now
        }
    
    if realtime or market_price_data.get('price', 0) > 0:
        CACHE[cache_key] = {
            'valuation': realtime.get('valuation', 0) if realtime else 0,
            'change': realtime.get('change', '') if realtime else '',
            'market_price': market_price_data,
            'time': now
        }
    
    return {
        'realtime': realtime if realtime else {'nav': 0, 'valuation': 0, 'change': '', 'update_time': ''},
        'market_price': market_price_data if market_price_data else {'price': 0, 'change_percent': 0},
        'time': now
    }

def get_fund_status(code):
    """
    获取基金申购/赎回状态（天天基金基本信息页面，带缓存）
    
    Args:
        code: 基金代码
    
    Returns:
        dict: 包含subscribe_status/redeem_status/limit_amount
    """
    cache_key = f'status_{code}'
    now = time.time()
    
    # 检查缓存, 未过期直接返回
    if cache_key in STATUS_CACHE and now - STATUS_CACHE[cache_key].get('time', 0) < STATUS_CACHE_EXPIRE:
        logger.debug(f"[CACHE] 基金{code} - 命中状态缓存")
        return STATUS_CACHE[cache_key]
    
    url = f'https://fundf10.eastmoney.com/jbgk_{code}.html'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://fund.eastmoney.com/'
    }
    
    start_time = time.time()
    logger.debug(f"[REQUEST] 天天基金基本信息 - URL: {url}")
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        elapsed = round((time.time() - start_time) * 1000, 2)
        
        logger.debug(f"[RESPONSE] 状态码: {resp.status_code}, 耗时: {elapsed}ms")
        
        if resp.status_code == 200:
            content = resp.text
            
            # 提取申购状态
            subscribe_match = re.search(r'交易状态：<span>([^<]+)</span>', content)
            subscribe_status = subscribe_match.group(1).strip() if subscribe_match else ''
            
            # 提取赎回状态
            redeem_match = re.search(r'<span[^>]*>(开放赎回|暂停赎回|限制赎回)</span>', content)
            redeem_status = redeem_match.group(1).strip() if redeem_match else ''
            
            # 提取限制金额
            limit_amount = ''
            amount_match = re.search(r'单日累计购买上限([\d.]+)(万|元)', content)
            if amount_match:
                num_str = amount_match.group(1)
                unit = amount_match.group(2)
                num = float(num_str)
                # 去掉无意义的小数
                if num == int(num):
                    num_str = str(int(num))
                else:
                    num_str = f'{num:g}'
                limit_amount = f'{num_str}{unit}'
            
            result = {
                'subscribe_status': subscribe_status,
                'redeem_status': redeem_status,
                'limit_amount': limit_amount,
                'time': now
            }
            STATUS_CACHE[cache_key] = result
            logger.info(f"[SUCCESS] 基金{code} - 申购:{subscribe_status}, 赎回:{redeem_status}, 限额:{limit_amount}")
            return result
        else:
            logger.error(f"[ERROR] 基金{code} - HTTP状态码: {resp.status_code}")
            
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[ERROR] 基金{code} - 请求失败: {str(e)}, 耗时: {elapsed}ms")
    
    logger.warning(f"[FALLBACK] 基金{code} - 申赎状态查询失败")
    return {'subscribe_status': '', 'redeem_status': '', 'limit_amount': ''}




def format_fund_data(funds):
    """
    格式化基金数据列表(并发获取所有基金数据)

    Args:
        funds: 基金配置列表

    Returns:
        list: 格式化后的基金数据列表
    """
    codes = [f.get('code', '') for f in funds]

    # 并发提交所有任务
    futures = {EXECUTOR.submit(fetch_fund_data, code): code for code in codes}

    # 收集所有结果
    fund_data_map = {}
    for future in as_completed(futures):
        code = futures[future]
        fund_data_map[code] = future.result()

    # QDII_LOF基金获取状态信息(串行, 避免请求过快)
    fund_status_map = {}
    for f in funds:
        if f.get('type') == 'QDII_LOF':
            code = f.get('code', '')
            fund_status_map[code] = get_fund_status(code)

    # 格式化输出
    result = []
    for f in funds:
        code = f.get('code', '')

        fund_data = fund_data_map.get(code, {})
        realtime = fund_data.get('realtime')
        market_price_data = fund_data.get('market_price', {})

        nav = realtime.get('nav', 0) if realtime else 0
        valuation = realtime.get('valuation', 0) if realtime else 0
        change = realtime.get('change', '') if realtime else ''

        price = market_price_data.get('price', 0)
        change_percent = market_price_data.get('change_percent', 0)

        # 场内交易价不可用时，用估值作为有效价格代理（用于计算折溢价）
        effective_price = price if price > 0 else (valuation if valuation > 0 else 0)

        premium = ((effective_price - nav) / nav * 100) if nav > 0 and effective_price > 0 else 0

        valPremium = ((price - valuation) / valuation * 100) if valuation > 0 and price > 0 else 0
        
        item = {
            'code': code,
            'name': f.get('name', ''),
            'price': price if price > 0 else '',
            'change': change,
            'change_percent': change_percent if change_percent != 0 else '',
            'premium': round(premium, 2) if premium else '',
            'nav': nav if nav > 0 else '',
            'space': round(premium, 1) if premium else '',
            'valuation': valuation if valuation > 0 else '',
            'valPremium': round(valPremium, 2) if valPremium else '',
        }

        # QDII_LOF基金添加申购/赎回状态
        if f.get('type') == 'QDII_LOF':
            # 过滤无场内交易价格的基金（场外QDII）
            if price <= 0:
                continue
            status = fund_status_map.get(code, {})
            item['subscribe_status'] = status.get('subscribe_status', '')
            item['redeem_status'] = status.get('redeem_status', '')
            item['limit_amount'] = status.get('limit_amount', '')

        result.append(item)
    return result

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/history.html')
def history():
    """历史数据页面"""
    return render_template('history.html')

@app.route('/api/lof')
def api_lof():
    """
    获取LOF基金列表(分页)
    
    Query参数:
        page: 页码, 默认1
        page_size: 每页数量, 默认500
    """
    config = load_config(LOF_CONFIG)
    if config and 'funds' in config:
        funds = config['funds']
        data = format_fund_data(funds)
    else:
        data = []
    
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 500, type=int)
    total = len(data)
    start = (page - 1) * page_size
    end = start + page_size
    paged_data = data[start:end]
    
    return jsonify({
        'success': True,
        'data': paged_data,
        'total': total,
        'page': page,
        'page_size': page_size,
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/qdii')
def api_qdii():
    """
    获取QDII基金列表(分页)
    
    Query参数:
        page: 页码, 默认1
        page_size: 每页数量, 默认500
    """
    config = load_config(QDII_CONFIG)
    if config and 'funds' in config:
        funds = config['funds']
        data = format_fund_data(funds)
    else:
        data = []
    
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 500, type=int)
    total = len(data)
    start = (page - 1) * page_size
    end = start + page_size
    paged_data = data[start:end]
    
    return jsonify({
        'success': True,
        'data': paged_data,
        'total': total,
        'page': page,
        'page_size': page_size,
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """清空所有缓存, 强制重新获取"""
    global CACHE, NAV_CACHE, STATUS_CACHE
    CACHE = {}
    NAV_CACHE = {}
    STATUS_CACHE = {}
    return jsonify({
        'success': True,
        'message': 'Cache cleared',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/fund/<code>')
def api_fund(code):
    """获取单只基金实时数据"""
    data = get_fund_realtime(code)
    if data:
        return jsonify({
            'success': True,
            'code': code,
            'data': data,
            'timestamp': datetime.datetime.now().isoformat()
        })
    else:
        return jsonify({
            'success': False,
            'code': code,
            'message': '无法获取数据',
            'timestamp': datetime.datetime.now().isoformat()
        })

@app.route('/api/fund/batch', methods=['POST'])
def api_fund_batch():
    """批量获取基金实时数据(已废弃, 使用并发模式)"""
    codes = request.json.get('codes', [])
    results = {}
    for code in codes:
        data = get_fund_realtime(code)
        if data:
            results[code] = data
        time.sleep(random.uniform(0.1, 0.3))
    
    return jsonify({
        'success': True,
        'data': results,
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/etf')
def api_etf():
    """获取ETF数据(模拟数据)"""
    return jsonify({
        'success': True,
        'data': [
            {'code': '513050', 'name': '中证500ETF', 'price': 3.4523, 'change': 1.23, 'iopv': 3.4612, 'premium': -0.26, 'space': 0.8},
            {'code': '513300', 'name': '沪深300ETF', 'price': 4.1234, 'change': 0.89, 'iopv': 4.1356, 'premium': -0.30, 'space': 0.9},
            {'code': '159919', 'name': '创业板ETF', 'price': 2.5678, 'change': 2.34, 'iopv': 2.5712, 'premium': -0.13, 'space': 0.5},
            {'code': '513500', 'name': '中证100ETF', 'price': 1.8923, 'change': -0.45, 'iopv': 1.8901, 'premium': 0.12, 'space': 0.3},
            {'code': '510300', 'name': '沪深300ETF', 'price': 4.5678, 'change': 1.56, 'iopv': 4.5523, 'premium': 0.34, 'space': 0.6},
        ],
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/option')
def api_option():
    """获取期权数据(模拟数据)"""
    return jsonify({
        'success': True,
        'data': [
            {'code': '510050', 'name': '50ETF', 'call': 3.10, 'put': 2.98, 'future': 6.08, 'space': 1.8, 'level': 'high'},
            {'code': '510300', 'name': '300ETF', 'call': 4.25, 'put': 4.12, 'future': 8.37, 'space': 1.2, 'level': 'medium'},
            {'code': '510500', 'name': '500ETF', 'call': 2.85, 'put': 2.72, 'future': 5.57, 'space': 0.9, 'level': 'medium'},
            {'code': '159919', 'name': '创业板', 'call': 2.60, 'put': 2.48, 'future': 5.08, 'space': 0.5, 'level': 'low'},
        ],
        'timestamp': datetime.datetime.now().isoformat()
    })

def get_history_from_file(code):
    """
    从文件读取历史数据
    
    Args:
        code: 基金代码
    
    Returns:
        dict: 历史数据对象, 不存在返回None
    """
    history_file = os.path.join(FUND_HISTORY_DIR, f'{code}.json')
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return None

LOG_CONF_FILE = os.path.join(BASE_DIR, 'config', 'logging.conf')

@app.route('/api/config')
def api_config():
    """获取前端配置(刷新间隔等)"""
    import configparser
    config = configparser.ConfigParser()
    config.read(LOG_CONF_FILE)
    return jsonify({
        'success': True,
        'refresh': {
            'trading_interval': config.getint('refresh', 'trading_interval', fallback=30000),
            'non_trading_interval': config.getint('refresh', 'non_trading_interval', fallback=900000),
        }
    })

@app.route('/api/history/<code>')
def api_history(code):
    """
    获取基金历史数据(带缓存)
    
    先从内存缓存读取, 没有则从文件读取并缓存
    """
    with HISTORY_LOCK:
        if code in HISTORY_CACHE:
            return jsonify({
                'success': True,
                'code': code,
                'data': HISTORY_CACHE[code],
                'timestamp': datetime.datetime.now().isoformat()
            })
    
    data = get_history_from_file(code)
    if data:
        with HISTORY_LOCK:
            HISTORY_CACHE[code] = data
        return jsonify({
            'success': True,
            'code': code,
            'data': data,
            'timestamp': datetime.datetime.now().isoformat()
        })
    else:
        return jsonify({
            'success': False,
            'code': code,
            'message': '无历史数据',
            'timestamp': datetime.datetime.now().isoformat()
        })

@app.route('/fund_history/<code>')
def serve_history_file(code):
    """静态文件访问历史数据"""
    return send_from_directory(FUND_HISTORY_DIR, f'{code}.json')

@app.route('/api/history/refresh', methods=['POST'])
def api_history_refresh():
    """清空历史数据缓存"""
    with HISTORY_LOCK:
        HISTORY_CACHE.clear()
    return jsonify({
        'success': True,
        'message': '历史数据缓存已刷新',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/history/generate/<code>', methods=['POST'])
def api_history_generate(code):
    """
    调用 generate_fund_history.py 重新生成基金历史数据（默认2000天）
    完成后清除该基金的内存缓存
    """
    import subprocess
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'generate_fund_history.py')
    try:
        logger.info(f"开始重新生成 {code} 历史数据(2000天)...")
        result = subprocess.run(
            [sys.executable, script_path, code, '--days', '2000'],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            with HISTORY_LOCK:
                HISTORY_CACHE.pop(code, None)
            logger.info(f"{code} 历史数据生成成功")
            return jsonify({
                'success': True,
                'message': f'{code} 历史数据已重新生成',
                'output': result.stdout.strip(),
                'timestamp': datetime.datetime.now().isoformat()
            })
        else:
            logger.warning(f"{code} 历史数据生成失败: {result.stderr}")
            return jsonify({
                'success': False,
                'message': '脚本执行失败',
                'error': result.stderr.strip(),
                'timestamp': datetime.datetime.now().isoformat()
            }), 500
    except subprocess.TimeoutExpired:
        logger.warning(f"{code} 历史数据生成超时")
        return jsonify({
            'success': False,
            'message': '生成超时',
            'timestamp': datetime.datetime.now().isoformat()
        }), 504
    except Exception as e:
        logger.error(f"{code} 历史数据生成异常: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

@app.route('/api/stats')
def api_stats():
    """获取统计信息(模拟数据)"""
    return jsonify({
        'lof': {'avgPremium': 2.34, 'opportunityCount': 8, 'maxPremium': 5.82, 'volume': 12340},
        'qdii': {'avgPremium': 3.21, 'opportunityCount': 5, 'maxPremium': 8.45, 'quota': 42.5},
        'etf': {'avgPremium': -0.12, 'opportunityCount': 3, 'maxDiscount': -0.85, 'ihValue': 8.92},
        'option': {'volDiff': 2.3, 'opportunityCount': 4, 'maxSpace': 1.8, 'volume': 56.7},
        'timestamp': datetime.datetime.now().isoformat()
    })

def preload_history():
    """后台预加载历史数据"""
    if not os.path.exists(FUND_HISTORY_DIR):
        return
    try:
        for filename in os.listdir(FUND_HISTORY_DIR):
            if filename.endswith('.json'):
                code = filename[:-5]
                data = get_history_from_file(code)
                if data:
                    with HISTORY_LOCK:
                        HISTORY_CACHE[code] = data
        print(f"历史数据预加载完成: {len(HISTORY_CACHE)} 只基金")
    except Exception as e:
        print(f"历史数据预加载失败: {e}")

def preload_funds():
    """后台预加载基金实时数据"""
    def _preload():
        time.sleep(2)
        print("开始预加载基金数据...")
        
        lof_config = load_config(LOF_CONFIG)
        qdii_config = load_config(QDII_CONFIG)
        
        codes = []
        if lof_config and 'funds' in lof_config:
            codes.extend([f.get('code') for f in lof_config['funds']])
        if qdii_config and 'funds' in qdii_config:
            codes.extend([f.get('code') for f in qdii_config['funds']])
        
        futures = {EXECUTOR.submit(fetch_fund_data, code): code for code in codes[:100]}
        for future in as_completed(futures):
            pass
        
        print(f"基金数据预加载完成: {len(CACHE)} 只基金")
    
    threading.Thread(target=_preload, daemon=True).start()

def check_port_in_use(port, host='0.0.0.0'):
    """检测端口是否已被占用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True

def find_pid_on_port(port):
    """查找占用端口的进程PID"""
    try:
        import psutil
        for conn in psutil.net_connections():
            if conn.laddr and conn.laddr.port == port and conn.pid:
                return conn.pid
    except ImportError:
        import subprocess
        try:
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
        except Exception:
            pass
    return None

def is_ancestor(pid):
    """判断 pid 是否为当前进程的祖先进程（含自身）"""
    import os
    current = os.getpid()
    if pid == current:
        return True
    try:
        import psutil
        current_proc = psutil.Process(current)
        for parent in current_proc.parents():
            if parent.pid == pid:
                return True
    except ImportError:
        pass
    return False

def kill_process_on_port(port):
    """强制关闭占用端口的非自身/非祖先进程"""
    import signal
    conflict_pid = find_pid_on_port(port)
    if conflict_pid is None:
        return False

    if is_ancestor(conflict_pid):
        logger.info(f'端口 {port} 由祖先进程 PID={conflict_pid} 持有，等待其释放...')
        return False

    try:
        import psutil
        proc = psutil.Process(conflict_pid)
        logger.warning(f"强制关闭进程 PID={conflict_pid} ({proc.name()})，释放端口 {port}")
        proc.send_signal(signal.SIGKILL)
        return True
    except ImportError:
        import subprocess
        try:
            result = subprocess.run(
                ['fuser', '-k', f'{port}/tcp'],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            pass
    return False

if __name__ == '__main__':
    logger.info('=' * 50)
    logger.info('启动套利系统服务')
    logger.info('=' * 50)

    # 检测端口冲突并自动清理（仅在非热重载子进程时执行）
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        if check_port_in_use(4000):
            logger.warning(f'端口 4000 已被占用，尝试自动释放...')
            if kill_process_on_port(4000):
                time.sleep(1)
            else:
                logger.error(f'端口 4000 被占用且无法自动释放，请手动关闭: kill -9 $(lsof -ti:4000)')
                logger.error(f'或使用脚本启动: bash scripts/start_app.sh')
                exit(1)

    # 启动后台预加载任务（仅在非热重载子进程时执行）
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        preload_history()
        preload_funds()
    
    logger.info(f'服务地址: http://0.0.0.0:4000')
    logger.info(f'LOF配置: {LOF_CONFIG}')
    logger.info(f'QDII配置: {QDII_CONFIG}')
    logger.info(f'历史数据目录: {FUND_HISTORY_DIR}')
    logger.info('=' * 50)
    
    app.run(debug=True, host='0.0.0.0', port=4000)