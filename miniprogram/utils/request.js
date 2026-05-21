// utils/request.js - 网络请求封装
const app = getApp();

/**
 * 封装wx.request，统一处理请求和响应
 * @param {Object} options 请求配置
 * @returns {Promise}
 */
function request(options) {
  return new Promise((resolve, reject) => {
    const { url, method = 'GET', data = {}, header = {} } = options;
    
    // 拼接完整URL
    const fullUrl = url.startsWith('http') ? url : `${app.globalData.baseUrl}${url}`;
    
    // 显示加载提示
    if (options.showLoading !== false) {
      wx.showLoading({
        title: options.loadingText || '加载中...',
        mask: true
      });
    }
    
    wx.request({
      url: fullUrl,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...header
      },
      timeout: options.timeout || 30000,
      success: (res) => {
        if (options.showLoading !== false) {
          wx.hideLoading();
        }
        
        // 请求成功
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          // HTTP错误
          const error = {
            code: res.statusCode,
            message: `请求失败：${res.statusCode}`,
            data: res.data
          };
          handleError(error);
          reject(error);
        }
      },
      fail: (err) => {
        if (options.showLoading !== false) {
          wx.hideLoading();
        }
        
        // 网络错误
        const error = {
          code: -1,
          message: '网络请求失败，请检查网络连接',
          data: err
        };
        handleError(error);
        reject(error);
      }
    });
  });
}

/**
 * 错误处理
 * @param {Object} error 错误对象
 */
function handleError(error) {
  console.error('请求错误：', error);
  
  // 显示错误提示
  wx.showToast({
    title: error.message || '请求失败',
    icon: 'none',
    duration: 3000
  });
}

/**
 * GET请求
 */
function get(url, data = {}, options = {}) {
  return request({
    url,
    method: 'GET',
    data,
    ...options
  });
}

/**
 * POST请求
 */
function post(url, data = {}, options = {}) {
  return request({
    url,
    method: 'POST',
    data,
    ...options
  });
}

/**
 * 批量请求
 */
function batchRequest(requests) {
  return Promise.all(requests.map(req => request(req)));
}

module.exports = {
  request,
  get,
  post,
  batchRequest
};
