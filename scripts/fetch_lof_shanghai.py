#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import json
import configparser
from datetime import datetime
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'fetch_lof_shanghai.log')
CONFIG_FILE = os.path.join(BASE_DIR, 'lof_config.json')
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

def setup_logger(name='fetch_lof_shanghai'):
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

def fetch_all_lof_akshare(logger):
    import akshare as ak
    
    logger.info("尝试使用akshare获取LOF数据")
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

def fetch_all_lof_rankhandler(logger):
    import requests
    import time
    import random
    
    logger.info("尝试使用东方财富rankhandler获取LOF数据")
    
    url = 'https://fund.eastmoney.com/data/rankhandler.aspx'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://fund.eastmoney.com/data/fundranking.html',
    }
    
    params = {
        'op': 'ph',
        'dt': 'kf',
        'ft': 'all',
        'pi': 1,
        'pn': 1000,
    }
    
    try:
        time.sleep(random.uniform(1, 3))
        session = requests.Session()
        session.headers.update(headers)
        
        logger.debug(f"调用接口: POST {url}")
        resp = session.post(url, params=params, timeout=30)
        
        if resp.status_code != 200:
            logger.warning(f"rankhandler返回状态码: {resp.status_code}")
            return None
        
        text = resp.text
        start = text.find('datas:"[') + 7
        end = text.find('"]', start)
        records = text[start:end].split('","')
        
        lofs = {}
        for rec in records:
            parts = rec.split(',')
            if len(parts) >= 2:
                code = parts[0]
                name = parts[1]
                if code.isdigit() and len(code) == 6:
                    if code.startswith('1') or 'LOF' in name.upper():
                        lofs[code] = name
        
        result = []
        for code, name in sorted(lofs.items(), key=lambda x: int(x[0])):
            result.append({
                'code': code,
                'name': name,
                'type': 'SHLOF',
                'source': 'eastmoney/rankhandler',
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        logger.info(f"东方财富rankhandler获取成功, 共 {len(result)} 只LOF基金")
        return result
        
    except Exception as e:
        logger.warning(f"东方财富rankhandler调用失败: {str(e)}")
        return None

def fetch_all_lof_searchapi(logger):
    import requests
    
    logger.info("尝试使用东方财富搜索API获取LOF数据")
    session = requests.Session()
    
    all_lofs = {}
    keywords = ['LOF', 'lof']
    
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
                if code.isdigit() and len(code) == 6 and code.startswith('1'):
                    if code not in all_lofs:
                        all_lofs[code] = name
        
        result = []
        for code, name in sorted(all_lofs.items(), key=lambda x: int(x[0])):
            result.append({
                'code': code,
                'name': name,
                'type': 'SHLOF',
                'source': 'eastmoney/searchapi',
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        logger.info(f"东方财富搜索API获取成功, 共 {len(result)} 只SHLOF基金")
        return result
        
    except Exception as e:
        logger.warning(f"东方财富搜索API调用失败: {str(e)}")
        return None

def fetch_all_lof_eastmoney(logger):
    import requests
    
    logger.info("尝试使用东方财富接口获取LOF数据")
    session = requests.Session()
    
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
        logger.info(f"东方财富接口返回: status={r.status_code}, length={len(r.text)}, text={r.text[:50] if r.text else 'empty'}")
        
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

def fetch_all_lof_fallback(logger):
    logger.info("使用备用LOF代码列表数据")
    
    # 已知的主流LOF基金代码列表
    LOFS = [
        ('161039', '易方达消费行业股票(LOF)'),
        ('161725', '招商丰庆灵活配置混合A'),
        ('160526', '华泰柏瑞量化增强混合A'),
        ('161832', '银华明仲策略优选混合A'),
        ('163406', '兴全合宜混合A'),
        ('160215', '嘉实原油主题股票(LOF)A'),
        ('166002', '中欧创新成长混合A'),
        ('161017', '富国天惠成长混合(LOF)A'),
        ('160322', '博时军工主题股票A'),
        ('161130', '易方达科创板50股票A'),
        ('501016', '国泰中证全指证券公司指数(LOF)'),
        ('501025', '华宝中证银行指数(LOF)A'),
        ('501038', '南方中证500指数(LOF)A'),
        ('160726', '景顺长城新兴成长混合A'),
        ('161903', '万家行业优选混合A'),
        ('167301', '方正富邦创新动力混合A'),
        ('165520', '博道中证500指数增强A'),
        ('162411', '华宝标普油气上证资源指数A'),
        ('501015', '国泰中证申万证券行业指数(LOF)A'),
        ('167303', '红土创新转型精选混合A'),
    ]
    
    data = []
    for code, name in LOFS:
        data.append({
            'code': code,
            'name': name if 'LOF' in name else name + '(LOF)',
            'type': 'SHLOF',
            'source': 'fallback',
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    logger.info(f"备用数据: 共 {len(data)} 只LOF基金")
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
    logger.info("LOF数据获取脚本启动")
    logger.info(f"日志级别: {logging.getLevelName(logger.level)}")
    
    data = None
    
    # 尝试多个数据源
    sources = [
        ('rankhandler', fetch_all_lof_rankhandler),
        ('akshare', fetch_all_lof_akshare),
        ('searchapi', fetch_all_lof_searchapi),
        ('fallback', fetch_all_lof_fallback),
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
        logger.info(f"完成! 共获取 {len(data)} 只LOF基金")
    else:
        logger.error("所有数据源均失败")
        # 最后尝试备用数据
        data = fetch_all_lof_fallback(logger)
        save_config(data, logger)
        logger.info(f"使用备用数据完成, 共 {len(data)} 只LOF基金")

if __name__ == '__main__':
    main()