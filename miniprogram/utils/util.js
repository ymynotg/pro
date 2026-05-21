// utils/util.js - 通用工具函数

/**
 * 格式化数字，保留指定小数位
 * @param {Number} num 数字
 * @param {Number} decimals 小数位数
 * @returns {String}
 */
function formatNumber(num, decimals = 2) {
  if (num === null || num === undefined || isNaN(num)) {
    return '--';
  }
  return Number(num).toFixed(decimals);
}

/**
 * 格式化百分比
 * @param {Number} num 数字
 * @param {Number} decimals 小数位数
 * @returns {String}
 */
function formatPercent(num, decimals = 2) {
  if (num === null || num === undefined || isNaN(num)) {
    return '--';
  }
  const value = Number(num);
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * 格式化价格
 * @param {Number} price 价格
 * @returns {String}
 */
function formatPrice(price) {
  return formatNumber(price, 3);
}

/**
 * 格式化时间
 * @param {Date|String|Number} time 时间
 * @param {String} format 格式
 * @returns {String}
 */
function formatTime(time, format = 'YYYY-MM-DD HH:mm:ss') {
  const date = new Date(time);
  
  if (isNaN(date.getTime())) {
    return '--';
  }
  
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  const second = String(date.getSeconds()).padStart(2, '0');
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hour)
    .replace('mm', minute)
    .replace('ss', second);
}

/**
 * 格式化金额（添加千分位）
 * @param {Number} amount 金额
 * @returns {String}
 */
function formatAmount(amount) {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '--';
  }
  
  const num = Number(amount);
  const parts = num.toFixed(2).split('.');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return parts.join('.');
}

/**
 * 防抖函数
 * @param {Function} fn 函数
 * @param {Number} delay 延迟时间
 * @returns {Function}
 */
function debounce(fn, delay = 500) {
  let timer = null;
  return function(...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

/**
 * 节流函数
 * @param {Function} fn 函数
 * @param {Number} interval 间隔时间
 * @returns {Function}
 */
function throttle(fn, interval = 500) {
  let lastTime = 0;
  return function(...args) {
    const now = Date.now();
    if (now - lastTime >= interval) {
      lastTime = now;
      fn.apply(this, args);
    }
  };
}

/**
 * 深拷贝
 * @param {Object} obj 对象
 * @returns {Object}
 */
function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(item => deepClone(item));
  }
  
  const cloned = {};
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      cloned[key] = deepClone(obj[key]);
    }
  }
  return cloned;
}

/**
 * 判断是否为空
 * @param {Any} value 值
 * @returns {Boolean}
 */
function isEmpty(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim() === '';
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value).length === 0;
  return false;
}

/**
 * 获取涨跌状态
 * @param {Number} value 涨跌值
 * @returns {String} 'up' | 'down' | 'flat'
 */
function getTrend(value) {
  if (value > 0) return 'up';
  if (value < 0) return 'down';
  return 'flat';
}

/**
 * 获取涨跌颜色类
 * @param {Number} value 涨跌值
 * @returns {String}
 */
function getTrendClass(value) {
  const trend = getTrend(value);
  const classMap = {
    'up': 'number-positive',
    'down': 'number-negative',
    'flat': 'text-muted'
  };
  return classMap[trend];
}

module.exports = {
  formatNumber,
  formatPercent,
  formatPrice,
  formatTime,
  formatAmount,
  debounce,
  throttle,
  deepClone,
  isEmpty,
  getTrend,
  getTrendClass
};
