// pages/history/history.js
const api = require('../../utils/api.js');
const util = require('../../utils/util.js');

Page({
  data: {
    // 基金信息
    fundCode: '',
    fundName: '',
    
    // 时间范围
    activeRange: 30,
    
    // 历史数据
    historyData: [],
    
    // 统计数据
    avgPremium: 0,
    maxPremium: 0,
    minPremium: 0,
    volatility: 0,
    
    // 图表相关
    showTooltip: false,
    tooltipX: 0,
    tooltipY: 0,
    tooltipDate: '',
    tooltipValue: '',
    
    // 加载状态
    loading: false
  },

  onLoad(options) {
    // 获取传递的参数
    const { code, name } = options;
    
    this.setData({
      fundCode: code || '',
      fundName: decodeURIComponent(name || '')
    });
    
    // 加载历史数据
    this.loadHistoryData();
  },

  onReady() {
    // 页面渲染完成，初始化图表
    this.chartContext = wx.createCanvasContext('premiumChart', this);
  },

  /**
   * 加载历史数据
   */
  async loadHistoryData() {
    this.setData({ loading: true });

    try {
      const { fundCode, activeRange } = this.data;
      
      // 计算日期范围
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - activeRange);
      
      // 调用API获取历史数据
      const res = await api.getHistoryData(fundCode, {
        start_date: util.formatTime(startDate, 'YYYY-MM-DD'),
        end_date: util.formatTime(endDate, 'YYYY-MM-DD')
      });
      
      const historyData = this.formatHistoryData(res.data || []);
      
      // 计算统计数据
      const stats = this.calculateStats(historyData);
      
      this.setData({
        historyData,
        ...stats
      });
      
      // 绘制图表
      if (historyData.length > 0) {
        this.drawChart(historyData);
      }
      
    } catch (error) {
      console.error('加载历史数据失败：', error);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  /**
   * 格式化历史数据
   */
  formatHistoryData(data) {
    return data.map(item => ({
      date: item.date || item.DATE,
      price: util.formatPrice(item.price || item.PRICE),
      nav: util.formatPrice(item.nav || item.NAV),
      premium: util.formatNumber(item.premium || item.PREMIUM_RATE, 2)
    })).sort((a, b) => new Date(b.date) - new Date(a.date));
  },

  /**
   * 计算统计数据
   */
  calculateStats(data) {
    if (data.length === 0) {
      return {
        avgPremium: 0,
        maxPremium: 0,
        minPremium: 0,
        volatility: 0
      };
    }
    
    const premiums = data.map(item => parseFloat(item.premium));
    
    const avgPremium = premiums.reduce((sum, val) => sum + val, 0) / premiums.length;
    const maxPremium = Math.max(...premiums);
    const minPremium = Math.min(...premiums);
    
    // 计算波动率（标准差）
    const variance = premiums.reduce((sum, val) => sum + Math.pow(val - avgPremium, 2), 0) / premiums.length;
    const volatility = Math.sqrt(variance);
    
    return {
      avgPremium: util.formatNumber(avgPremium, 2),
      maxPremium: util.formatNumber(maxPremium, 2),
      minPremium: util.formatNumber(minPremium, 2),
      volatility: util.formatNumber(volatility, 2)
    };
  },

  /**
   * 绘制图表
   */
  drawChart(data) {
    if (!this.chartContext || data.length === 0) return;
    
    const ctx = this.chartContext;
    const query = wx.createSelectorQuery().in(this);
    
    query.select('.chart-canvas').boundingClientRect((rect) => {
      if (!rect) return;
      
      const { width, height } = rect;
      const padding = 40;
      const chartWidth = width - padding * 2;
      const chartHeight = height - padding * 2;
      
      // 清空画布
      ctx.clearRect(0, 0, width, height);
      
      // 获取数据范围
      const premiums = data.map(item => parseFloat(item.premium));
      const minPremium = Math.min(...premiums);
      const maxPremium = Math.max(...premiums);
      const premiumRange = maxPremium - minPremium || 1;
      
      // 绘制坐标轴
      ctx.setStrokeStyle('#3a3a5a');
      ctx.setLineWidth(1);
      
      // Y轴
      ctx.beginPath();
      ctx.moveTo(padding, padding);
      ctx.lineTo(padding, height - padding);
      ctx.stroke();
      
      // X轴
      ctx.beginPath();
      ctx.moveTo(padding, height - padding);
      ctx.lineTo(width - padding, height - padding);
      ctx.stroke();
      
      // 绘制数据线
      ctx.setStrokeStyle('#00d4ff');
      ctx.setLineWidth(2);
      ctx.beginPath();
      
      data.forEach((item, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth;
        const y = height - padding - ((parseFloat(item.premium) - minPremium) / premiumRange) * chartHeight;
        
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      
      ctx.stroke();
      
      // 绘制数据点
      ctx.setFillStyle('#00d4ff');
      data.forEach((item, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth;
        const y = height - padding - ((parseFloat(item.premium) - minPremium) / premiumRange) * chartHeight;
        
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
      });
      
      ctx.draw();
    }).exec();
  },

  /**
   * 切换时间范围
   */
  changeRange(e) {
    const range = e.currentTarget.dataset.range;
    
    if (range === this.data.activeRange) return;
    
    this.setData({ activeRange: range });
    this.loadHistoryData();
  },

  /**
   * 图表触摸开始
   */
  onChartTouchStart(e) {
    this.showChartTooltip(e);
  },

  /**
   * 图表触摸移动
   */
  onChartTouchMove(e) {
    this.showChartTooltip(e);
  },

  /**
   * 图表触摸结束
   */
  onChartTouchEnd() {
    this.setData({ showTooltip: false });
  },

  /**
   * 显示图表提示
   */
  showChartTooltip(e) {
    const touch = e.touches[0];
    const { x, y } = touch;
    
    // 根据触摸位置计算对应的数据点
    const { historyData } = this.data;
    if (historyData.length === 0) return;
    
    // 简化处理：根据x坐标计算索引
    const query = wx.createSelectorQuery().in(this);
    query.select('.chart-canvas').boundingClientRect((rect) => {
      if (!rect) return;
      
      const padding = 40;
      const chartWidth = rect.width - padding * 2;
      const relativeX = x - rect.left - padding;
      
      if (relativeX < 0 || relativeX > chartWidth) {
        this.setData({ showTooltip: false });
        return;
      }
      
      const index = Math.round((relativeX / chartWidth) * (historyData.length - 1));
      const dataPoint = historyData[index];
      
      if (dataPoint) {
        this.setData({
          showTooltip: true,
          tooltipX: x - rect.left,
          tooltipY: y - rect.top - 80,
          tooltipDate: dataPoint.date,
          tooltipValue: dataPoint.premium
        });
      }
    }).exec();
  }
});
