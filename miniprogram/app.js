// app.js
App({
  globalData: {
    // 后端API基础URL - 需要配置为实际的服务器地址
    // 注意：小程序要求使用HTTPS域名，需要在微信公众平台配置合法域名
    baseUrl: 'https://app.moutai519.com.cn', // 请替换为实际域名
    
    // 数据刷新间隔（毫秒）
    refreshInterval: 30000,
    
    // 用户设置
    settings: {
      autoRefresh: true,
      showCleanedData: true
    }
  },

  onLaunch() {
    // 小程序启动时执行
    console.log('小程序启动');
    
    // 检查更新
    this.checkUpdate();
    
    // 获取系统信息
    this.getSystemInfo();
  },

  // 检查小程序更新
  checkUpdate() {
    if (wx.canIUse('getUpdateManager')) {
      const updateManager = wx.getUpdateManager();
      
      updateManager.onCheckForUpdate((res) => {
        console.log('是否有新版本：', res.hasUpdate);
      });

      updateManager.onUpdateReady(() => {
        wx.showModal({
          title: '更新提示',
          content: '新版本已经准备好，是否重启应用？',
          success: (res) => {
            if (res.confirm) {
              updateManager.applyUpdate();
            }
          }
        });
      });

      updateManager.onUpdateFailed(() => {
        wx.showToast({
          title: '更新失败，请重试',
          icon: 'none'
        });
      });
    }
  },

  // 获取系统信息
  getSystemInfo() {
    const systemInfo = wx.getSystemInfoSync();
    this.globalData.systemInfo = systemInfo;
    console.log('系统信息：', systemInfo);
  }
});
