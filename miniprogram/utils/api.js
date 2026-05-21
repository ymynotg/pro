// utils/api.js - API接口定义
const { get, post } = require('./request.js');

/**
 * 获取LOF基金数据
 */
function getLOFData(params = {}) {
  return get('/api/lof', params);
}

/**
 * 获取QDII基金数据
 */
function getQDIIData(params = {}) {
  return get('/api/qdii', params);
}

/**
 * 获取ETF基金数据
 */
function getETFData(params = {}) {
  return get('/api/etf', params);
}

/**
 * 获取期权数据
 */
function getOptionData(params = {}) {
  return get('/api/option', params);
}

/**
 * 获取单只基金详情
 * @param {String} code 基金代码
 */
function getFundDetail(code) {
  return get(`/api/fund/${code}`);
}

/**
 * 批量查询基金
 * @param {Array} codes 基金代码数组
 */
function batchQueryFunds(codes) {
  return post('/api/fund/batch', { codes });
}

/**
 * 获取历史数据
 * @param {String} code 基金代码
 * @param {Object} params 查询参数
 */
function getHistoryData(code, params = {}) {
  return get(`/api/history/${code}`, params);
}

/**
 * 刷新数据
 */
function refreshData() {
  return post('/api/refresh');
}

/**
 * 获取配置信息
 */
function getConfig() {
  return get('/api/config');
}

/**
 * 获取统计信息
 */
function getStats() {
  return get('/api/stats');
}

module.exports = {
  getLOFData,
  getQDIIData,
  getETFData,
  getOptionData,
  getFundDetail,
  batchQueryFunds,
  getHistoryData,
  refreshData,
  getConfig,
  getStats
};
