// pages/index/index.js
const api = require('../../utils/api.js');
const util = require('../../utils/util.js');
const app = getApp();

Page({
  data: {
    // 当前激活的标签
    activeTab: 'lof',
    
    // 各类型数据
    lofData: [],
    qdiiData: [],
    etfData: [],
    optionData: [],
    
    // 数据计数
    lofCount: 0,
    qdiiCount: 0,
    etfCount: 0,
    optionCount: 0,
    
    // 筛选后的数据
    filteredData: [],
    
    // 统计数据
    positiveCount: 0,
    negativeCount: 0,
    updateTime: '--',
    
    // 搜索关键词
    searchKeyword: '',
    
    // 是否显示清洗数据
    showCleanedData: true,
    
    // 加载状态
    loading: false,
    
    // 自动刷新定时器
    refreshTimer: null
  },

  onLoad() {
    // 页面加载时获取数据
    this.loadData();
  },

  onShow() {
    // 页面显示时启动自动刷新
    this.startAutoRefresh();
  },

  onHide() {
    // 页面隐藏时停止自动刷新
    this.stopAutoRefresh();
  },

  onUnload() {
    // 页面卸载时停止自动刷新
    this.stopAutoRefresh();
  },

  onPullDownRefresh() {
    // 下拉刷新
    this.loadData().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载数据
   */
  async loadData() {
    this.setData({ loading: true });

    try {
      // 根据当前标签加载对应数据
      const tab = this.data.activeTab;
      
      let data = [];
      switch (tab) {
        case 'lof':
          data = await this.loadLOFData();
          break;
        case 'qdii':
          data = await this.loadQDIIData();
          break;
        case 'etf':
          data = await this.loadETFData();
          break;
        case 'option':
          data = await this.loadOptionData();
          break;
      }
      
      // 更新数据
      this.updateData(tab, data);
      
    } catch (error) {
      console.error('加载数据失败：', error);
      wx.showToast({
        title: '加载失败，请重试',
        icon: 'none'
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  /**
   * 加载LOF数据
   */
  async loadLOFData() {
    try {
      const res = await api.getLOFData();
      return this.formatData(res.data || []);
    } catch (error) {
      console.error('加载LOF数据失败：', error);
      return [];
    }
  },

  /**
   * 加载QDII数据
   */
  async loadQDIIData() {
    try {
      const res = await api.getQDIIData();
      let data = this.formatData(res.data || []);
      
      // 如果开启数据清洗，过滤掉异常数据
      if (this.data.showCleanedData) {
        data = this.cleanQDIIData(data);
      }
      
      return data;
    } catch (error) {
      console.error('加载QDII数据失败：', error);
      return [];
    }
  },

  /**
   * 加载ETF数据
   */
  async loadETFData() {
    try {
      const res = await api.getETFData();
      return this.formatData(res.data || []);
    } catch (error) {
      console.error('加载ETF数据失败：', error);
      return [];
    }
  },

  /**
   * 加载期权数据
   */
  async loadOptionData() {
    try {
      const res = await api.getOptionData();
      return this.formatData(res.data || []);
    } catch (error) {
      console.error('加载期权数据失败：', error);
      return [];
    }
  },

  /**
   * 格式化数据
   */
  formatData(data) {
    return data.map(item => ({
      ...item,
      price: util.formatPrice(item.price),
      nav: util.formatPrice(item.nav),
      estimate: util.formatPrice(item.estimate),
      changePercent: util.formatNumber(item.change_percent || item.changePercent, 2),
      premiumRate: util.formatNumber(item.premium_rate || item.premiumRate, 2)
    }));
  },

  /**
   * 清洗QDII数据
   */
  cleanQDIIData(data) {
    return data.filter(item => {
      // 过滤掉异常数据
      const price = parseFloat(item.price);
      const nav = parseFloat(item.nav);
      const premium = parseFloat(item.premiumRate);
      
      // 价格和净值必须大于0
      if (price <= 0 || nav <= 0) return false;
      
      // 溢价率在合理范围内（-50% ~ 50%）
      if (Math.abs(premium) > 50) return false;
      
      return true;
    });
  },

  /**
   * 更新数据
   */
  updateData(tab, data) {
    const count = data.length;
    const positiveCount = data.filter(item => parseFloat(item.premiumRate) > 0).length;
    const negativeCount = data.filter(item => parseFloat(item.premiumRate) < 0).length;
    
    this.setData({
      [`${tab}Data`]: data,
      [`${tab}Count`]: count,
      filteredData: data,
      positiveCount,
      negativeCount,
      updateTime: util.formatTime(new Date(), 'HH:mm:ss')
    });
  },

  /**
   * 切换标签
   */
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    
    if (tab === this.data.activeTab) return;
    
    this.setData({
      activeTab: tab,
      searchKeyword: '',
      filteredData: []
    });
    
    // 加载对应标签的数据
    this.loadData();
  },

  /**
   * 搜索输入
   */
  onSearchInput: util.debounce(function(e) {
    const keyword = e.detail.value.trim();
    this.setData({ searchKeyword: keyword });
    this.filterData();
  }, 300),

  /**
   * 执行搜索
   */
  onSearch(e) {
    const keyword = e.detail.value.trim();
    this.setData({ searchKeyword: keyword });
    this.filterData();
  },

  /**
   * 清空搜索
   */
  clearSearch() {
    this.setData({ searchKeyword: '' });
    this.filterData();
  },

  /**
   * 筛选数据
   */
  filterData() {
    const tab = this.data.activeTab;
    const keyword = this.data.searchKeyword.toLowerCase();
    let data = this.data[`${tab}Data`] || [];
    
    if (keyword) {
      data = data.filter(item => {
        return item.code.toLowerCase().includes(keyword) ||
               item.name.toLowerCase().includes(keyword);
      });
    }
    
    const positiveCount = data.filter(item => parseFloat(item.premiumRate) > 0).length;
    const negativeCount = data.filter(item => parseFloat(item.premiumRate) < 0).length;
    
    this.setData({
      filteredData: data,
      positiveCount,
      negativeCount
    });
  },

  /**
   * 切换数据清洗
   */
  toggleCleanFilter() {
    this.setData({
      showCleanedData: !this.data.showCleanedData
    });
    
    // 重新加载QDII数据
    if (this.data.activeTab === 'qdii') {
      this.loadData();
    }
  },

  /**
   * 刷新数据
   */
  async refreshData() {
    wx.showLoading({ title: '刷新中...' });
    
    try {
      // 调用后端刷新接口
      await api.refreshData();
      
      // 重新加载数据
      await this.loadData();
      
      wx.showToast({
        title: '刷新成功',
        icon: 'success'
      });
    } catch (error) {
      console.error('刷新失败：', error);
      wx.showToast({
        title: '刷新失败',
        icon: 'none'
      });
    }
  },

  /**
   * 查看详情
   */
  viewDetail(e) {
    const item = e.currentTarget.dataset.item;
    
    // 跳转到历史页面
    wx.navigateTo({
      url: `/pages/history/history?code=${item.code}&name=${encodeURIComponent(item.name)}`
    });
  },

  /**
   * 启动自动刷新
   */
  startAutoRefresh() {
    if (!app.globalData.settings.autoRefresh) return;
    
    this.stopAutoRefresh();
    
    this.data.refreshTimer = setInterval(() => {
      this.loadData();
    }, app.globalData.refreshInterval);
  },

  /**
   * 停止自动刷新
   */
  stopAutoRefresh() {
    if (this.data.refreshTimer) {
      clearInterval(this.data.refreshTimer);
      this.data.refreshTimer = null;
    }
  }
});
