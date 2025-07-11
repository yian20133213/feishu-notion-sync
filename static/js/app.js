        // 全局错误处理器 - 捕获undefined错误
        window.addEventListener('error', function(e) {
            console.error('🔥 全局JavaScript错误:', {
                message: e.message,
                filename: e.filename,
                lineno: e.lineno,
                colno: e.colno,
                stack: e.error?.stack
            });
            
            if (e.message.includes('undefined')) {
                console.error('🚨 检测到undefined相关错误:', e.message);
                console.trace('错误堆栈追踪');
            }
        });
        
        // 全局页面导航变量
        let navItems, mobileNavItems, pages, pageTitle;
        let currentPage = 'dashboard';
        
        const titles = {
            'dashboard': '仪表板',
            'configs': '配置管理',
            'monitoring': '监控中心', 
            'data': '数据管理',
            'settings': '系统设置',
            'versions': '版本历史',
            'help': '帮助支持'
        };
        
        // 全局showPage函数
        function showPage(pageId) {
            console.log(`切换到页面: ${pageId}`);
            
            // 隐藏所有页面
            if (pages) {
                pages.forEach(page => page.classList.add('hidden'));
            }
            
            // 显示目标页面
            const targetPage = document.getElementById(pageId + '-page');
            if (targetPage) {
                targetPage.classList.remove('hidden');
                console.log(`页面 ${pageId} 已显示`);
            } else {
                console.error(`页面 ${pageId} 不存在`);
                return;
            }
            
            // 更新页面标题
            if (pageTitle && titles[pageId]) {
                pageTitle.textContent = titles[pageId];
            }
            
            // 更新当前页面追踪 (用于智能刷新)
            currentPage = pageId;
            
            // 更新导航状态
            if (navItems && mobileNavItems) {
                [...navItems, ...mobileNavItems].forEach(item => {
                    item.classList.remove('nav-active');
                    item.classList.add('text-gray-600');
                });
                
                [...navItems, ...mobileNavItems].forEach(item => {
                    if (item.getAttribute('href') === '#' + pageId) {
                        item.classList.add('nav-active');
                        item.classList.remove('text-gray-600');
                    }
                });
            }
            
            // 页面切换时加载对应数据
            if (pageId === 'configs') {
                loadConfigs();
            } else if (pageId === 'dashboard') {
                // 初始化仪表盘图表
                setTimeout(() => {
                    initDashboardChart();
                }, 100);
                
                // 加载仪表盘数据
                loadDashboardData();
                loadSyncHistory();
                loadProcessorStatus();
            } else if (pageId === 'monitoring') {
                // 确保图表容器可见后再初始化和加载数据
                setTimeout(() => {
                    console.log('初始化监控页面...');
                    initMonitoringCharts();
                    loadMonitoringSyncRecords();
                    loadPerformanceData();
                    loadRealtimeData();
                    loadMonitoringStats();
                    console.log('监控页面初始化完成');
                }, 200);
            } else if (pageId === 'data') {
                // 立即初始化分页控制
                initDataPagePagination();
                // 加载数据管理页面的默认数据
                refreshDataView();
            } else if (pageId === 'settings') {
                loadSystemSettings();
            } else if (pageId === 'help') {
                initHelpPage();
            }
        }

        // 页面导航功能
        function initNavigation() {
            navItems = document.querySelectorAll('.nav-item');
            mobileNavItems = document.querySelectorAll('.mobile-nav-item');
            pages = document.querySelectorAll('.page-content');
            pageTitle = document.getElementById('page-title');
            
            // 绑定导航事件
            [...navItems, ...mobileNavItems].forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    const href = item.getAttribute('href');
                    const pageId = href.substring(1);
                    showPage(pageId);
                    
                    // 移动端导航后关闭侧边栏
                    if (item.classList.contains('mobile-nav-item')) {
                        closeMobileSidebar();
                    }
                });
            });
        }
        
        // 移动端菜单功能
        function initMobileMenu() {
            const mobileMenuBtn = document.getElementById('mobile-menu-btn');
            const mobileCloseBtn = document.getElementById('mobile-close-btn');
            const mobileSidebar = document.getElementById('mobile-sidebar');
            const mobileOverlay = document.getElementById('mobile-overlay');
            
            function openMobileSidebar() {
                mobileSidebar.classList.remove('-translate-x-full');
                mobileOverlay.classList.remove('hidden');
                document.body.classList.add('overflow-hidden');
            }
            
            function closeMobileSidebar() {
                // 新版本的侧边栏控制
                const sidebar = document.getElementById('sidebar');
                if (sidebar) {
                    sidebar.classList.remove('open');
                }
                
                // 兼容旧版本
                if (mobileSidebar) {
                    mobileSidebar.classList.add('-translate-x-full');
                }
                if (mobileOverlay) {
                    mobileOverlay.classList.add('hidden');
                }
                document.body.classList.remove('overflow-hidden');
            }
            
            // 绑定事件
            if (mobileMenuBtn) {
                mobileMenuBtn.addEventListener('click', openMobileSidebar);
            }
            
            if (mobileCloseBtn) {
                mobileCloseBtn.addEventListener('click', closeMobileSidebar);
            }
            
            if (mobileOverlay) {
                mobileOverlay.addEventListener('click', closeMobileSidebar);
            }
            
            // 暴露函数给全局使用
            window.closeMobileSidebar = closeMobileSidebar;
        }
        
        // 增强的客户端数据缓存系统
        const dataCache = {
            dashboard: { data: null, timestamp: 0, ttl: 60000 }, // 1分钟缓存
            configs: { data: null, timestamp: 0, ttl: 120000 },  // 2分钟缓存
            history: { data: null, timestamp: 0, ttl: 30000 },   // 30秒缓存
            monitoring: { data: null, timestamp: 0, ttl: 45000 }, // 45秒缓存
            sync_records: { data: null, timestamp: 0, ttl: 30000 }, // 30秒缓存
            stats: { data: null, timestamp: 0, ttl: 90000 },      // 90秒缓存
            images: { data: null, timestamp: 0, ttl: 120000 }     // 2分钟缓存
        };
        
        // 缓存键生成器 - 考虑参数差异
        function generateCacheKey(baseKey, params = {}) {
            const paramString = Object.keys(params)
                .sort()
                .map(key => `${key}=${params[key]}`)
                .join('&');
            return paramString ? `${baseKey}_${paramString}` : baseKey;
        }
        
        // 增强的缓存管理函数
        function getCachedData(key, params = {}) {
            const cacheKey = generateCacheKey(key, params);
            const cached = dataCache[cacheKey] || dataCache[key];
            if (cached && cached.data && (Date.now() - cached.timestamp) < cached.ttl) {
                console.log(`[Cache] 命中缓存: ${cacheKey}`);
                return cached.data;
            }
            return null;
        }
        
        function setCachedData(key, data, params = {}) {
            const cacheKey = generateCacheKey(key, params);
            if (!dataCache[cacheKey]) {
                dataCache[cacheKey] = { data: null, timestamp: 0, ttl: dataCache[key]?.ttl || 60000 };
            }
            dataCache[cacheKey].data = data;
            dataCache[cacheKey].timestamp = Date.now();
            console.log(`[Cache] 更新缓存: ${cacheKey}`);
        }
        
        // 缓存失效函数
        function invalidateCache(pattern) {
            Object.keys(dataCache).forEach(key => {
                if (key.includes(pattern)) {
                    dataCache[key].timestamp = 0;
                    console.log(`[Cache] 失效缓存: ${key}`);
                }
            });
        }
        
        // 清理过期缓存
        function cleanExpiredCache() {
            const now = Date.now();
            Object.keys(dataCache).forEach(key => {
                const cached = dataCache[key];
                if (cached && (now - cached.timestamp) >= cached.ttl) {
                    cached.data = null;
                    cached.timestamp = 0;
                }
            });
        }
        
        // 加载同步任务处理器状态
        function loadProcessorStatus() {
            return fetch('/api/v1/sync/processor/status')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateProcessorStatus(data.processor);
                        return data.processor;
                    } else {
                        console.error('获取处理器状态失败:', data.message);
                        updateProcessorStatus(null);
                        return null;
                    }
                })
                .catch(error => {
                    console.error('获取处理器状态异常:', error);
                    updateProcessorStatus(null);
                    return null;
                });
        }
        
        function updateProcessorStatus(processor) {
            const statusElement = document.getElementById('processor-status');
            const pendingElement = document.getElementById('pending-tasks');
            const processingElement = document.getElementById('processing-tasks');
            
            if (processor && processor.running) {
                if (statusElement) {
                    statusElement.innerHTML = `
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            <span class="w-2 h-2 bg-green-400 rounded-full mr-1"></span>
                            运行中
                        </span>
                    `;
                }
                if (pendingElement) pendingElement.textContent = processor.pending_tasks || 0;
                if (processingElement) processingElement.textContent = processor.processing_tasks || 0;
            } else {
                if (statusElement) {
                    statusElement.innerHTML = `
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            <span class="w-2 h-2 bg-red-400 rounded-full mr-1"></span>
                            未运行
                        </span>
                    `;
                }
                if (pendingElement) pendingElement.textContent = '?';
                if (processingElement) processingElement.textContent = '?';
            }
        }

        // 数据加载和更新功能 - 优化缓存策略
        function loadDashboardData(forceRefresh = false) {
            // 总是强制刷新，避免显示过期的失败记录
            forceRefresh = true;
            
            // 检查缓存
            if (!forceRefresh) {
                const cached = getCachedData('dashboard');
                if (cached) {
                    updateDashboardStats(cached);
                    return Promise.resolve();
                }
            }
            
            console.log('加载仪表板数据...');
            
            return fetch('/api/v1/dashboard?_=' + Date.now())
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        updateDashboardStats(data.data);
                        setCachedData('dashboard', data.data);
                        console.log('仪表板数据加载完成');
                        
                        // 同时加载最近活动
                        loadRecentActivities();
                    } else {
                        console.warn('仪表板数据加载失败:', data.message);
                    }
                })
                .catch(error => {
                    console.error('获取仪表板数据失败:', error);
                    // 使用默认数据
                    const defaultData = {
                        total_configs: 0,
                        active_configs: 0,
                        total_records: 0,
                        success_rate: 0,
                        failed_records: 0,
                        pending_records: 0
                    };
                    updateDashboardStats(defaultData);
                });
        }
        
        function updateDashboardStats(data) {
            console.log('更新仪表板统计数据:', data);
            
            // 更新启用配置数量
            const configsCard = document.querySelector('[data-stat="configs"]');
            if (configsCard) {
                configsCard.textContent = data.active_configs || 0;
            }
            
            // 更新待处理任务
            const runningCard = document.querySelector('[data-stat="running"]');
            if (runningCard) {
                runningCard.textContent = data.pending_records || 0;
            }
            
            // 更新成功率
            const successRateCard = document.querySelector('[data-stat="success-rate"]');
            if (successRateCard) {
                const successRate = data.success_rate || 0;
                successRateCard.textContent = successRate.toFixed(1) + '%';
            }
            
            // 更新失败记录数
            const errorsCard = document.querySelector('[data-stat="errors"]');
            if (errorsCard) {
                errorsCard.textContent = data.failed_records || 0;
            }
        }
        
        function loadSyncHistory(forceRefresh = false) {
            // 检查缓存
            if (!forceRefresh) {
                const cached = getCachedData('history');
                if (cached) {
                    updateSyncHistoryList(cached);
                    updateDataRecordsTable(cached); // 同时更新数据管理页面的表格
                    return Promise.resolve();
                }
            }
            
            console.log('加载同步历史...');
            
            return fetch('/api/v1/sync/records?limit=20&_=' + Date.now())
                .then(response => {
                    if (!response.ok) {
                        // 尝试旧版API
                        return fetch('/api/v1/sync/history?limit=20');
                    }
                    return response;
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('同步历史响应:', data);
                    
                    if (data.success) {
                        // 处理数据结构
                        let history = [];
                        
                        if (data.data) {
                            if (Array.isArray(data.data)) {
                                history = data.data;
                            } else if (data.data.items) {
                                history = data.data.items;
                            }
                        } else if (Array.isArray(data.records)) {
                            history = data.records;
                        }
                        
                        updateSyncHistoryList(history);
                        updateDataRecordsTable(history); // 同时更新数据管理页面的表格
                        setCachedData('history', history);
                        console.log('同步历史加载完成，记录数:', history.length);
                    } else {
                        console.warn('同步历史加载失败:', data.message || data.error);
                        updateSyncHistoryList([]);
                        updateDataRecordsTable([]); // 同时更新数据管理页面的表格
                    }
                })
                .catch(error => {
                    console.error('获取同步历史失败:', error);
                    updateSyncHistoryList([]);
                    updateDataRecordsTable([]); // 同时更新数据管理页面的表格
                });
        }
        
        function updateSyncHistoryList(history) {
            const container = document.querySelector('#sync-history-list');
            if (!container) {
                console.warn('同步历史容器未找到');
                return;
            }
            
            // 确保history是数组
            if (!Array.isArray(history)) {
                history = [];
            }
            
            if (history.length === 0) {
                container.innerHTML = `
                    <div class="flex items-center justify-center p-8 text-gray-500">
                        <i class="fas fa-history mr-2"></i>
                        <span>暂无同步历史记录</span>
                        <button onclick="loadSyncHistory(true)" class="ml-4 px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600">
                            刷新
                        </button>
                    </div>
                `;
                return;
            }
            
            // 生成历史记录HTML
            const historyHTML = history.map(record => {
                // 统一状态处理
                const status = record.sync_status || record.status || 'pending';
                const statusClass = status === 'success' || status === 'completed' ? 'text-green-600' : 
                                  status === 'failed' || status === 'error' ? 'text-red-600' : 
                                  status === 'processing' ? 'text-blue-600' : 'text-yellow-600';
                const statusIcon = status === 'success' || status === 'completed' ? 'fa-check-circle' : 
                                 status === 'failed' || status === 'error' ? 'fa-times-circle' : 
                                 status === 'processing' ? 'fa-spinner fa-spin' : 'fa-clock';
                
                // 状态文本
                const statusText = status === 'success' || status === 'completed' ? '同步成功' : 
                                 status === 'failed' || status === 'error' ? '同步失败' : 
                                 status === 'processing' ? '同步中' : '等待同步';
                
                // 文档标题处理
                const documentTitle = record.document_title || record.title || 
                                    (record.source_id ? `文档 ${record.source_id.substring(0, 8)}...` : '未知文档');
                
                // 记录编号显示
                const recordNumber = record.record_number ? `#${record.record_number}` : '';
                
                return `
                    <div class="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-3">
                                <i class="fas ${statusIcon} ${statusClass}"></i>
                                <div>
                                    <div class="font-medium text-gray-900">
                                        ${documentTitle}
                                        ${recordNumber ? `<span class="text-xs text-gray-400 ml-2">${recordNumber}</span>` : ''}
                                    </div>
                                    <div class="text-sm text-gray-500">
                                        ${record.source_platform || '飞书'} → ${record.target_platform || 'Notion'}
                                    </div>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="text-sm text-gray-500">
                                    ${getTimeAgo(record.created_at || record.updated_at || new Date().toISOString())}
                                </div>
                                <div class="text-xs ${statusClass}">
                                    ${statusText}
                                </div>
                            </div>
                        </div>
                        ${record.error_message ? `
                            <div class="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                                <i class="fas fa-exclamation-triangle mr-1"></i>
                                ${record.error_message}
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
            
            container.innerHTML = historyHTML;
        }
        
        function getTimeAgo(dateString) {
            if (!dateString) return 'N/A';
            
            try {
                // 处理多种时间格式
                let date;
                if (dateString.includes('T')) {
                    // ISO格式: 2024-06-26T12:30:45.123456 或 2024-06-26T12:30:45Z
                    date = new Date(dateString);
                } else if (dateString.includes('-')) {
                    // 其他格式: 2024-06-26 12:30:45 (已经是北京时间)
                    // 直接当作本地时间处理，不需要时区转换
                    date = new Date(dateString);
                } else {
                    // 时间戳
                    date = new Date(parseInt(dateString));
                }
                
                // 检查日期是否有效
                if (isNaN(date.getTime())) {
                    return '时间格式错误';
                }
                
                const now = new Date();
                const diffMs = now - date;
                const diffMins = Math.floor(diffMs / 60000);
                const diffHours = Math.floor(diffMs / 3600000);
                const diffDays = Math.floor(diffMs / 86400000);
                
                // 优化时间显示逻辑
                if (diffMs < 0) {
                    // 未来时间（可能是服务器时间同步问题）
                    return '刚刚';
                }
                
                if (diffMins < 1) return '刚刚';
                if (diffMins < 60) return `${diffMins}分钟前`;
                if (diffHours < 24) return `${diffHours}小时前`;
                if (diffDays < 30) return `${diffDays}天前`;
                
                // 超过30天显示具体日期和时间
                return date.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
            } catch (error) {
                console.error('时间解析错误:', error, dateString);
                return '时间解析失败';
            }
        }

        // 格式化完整时间显示
        function formatFullTime(dateString) {
            if (!dateString) return 'N/A';
            
            try {
                let date;
                if (dateString.includes('T')) {
                    date = new Date(dateString);
                } else if (dateString.includes('-')) {
                    // 直接当作本地时间处理，因为后端已经返回北京时间
                    date = new Date(dateString);
                } else {
                    date = new Date(parseInt(dateString));
                }
                
                if (isNaN(date.getTime())) {
                    return '时间格式错误';
                }
                
                return date.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    weekday: 'short'
                });
                
            } catch (error) {
                console.error('时间格式化错误:', error, dateString);
                return '时间格式化失败';
            }
        }

        // 更新页面中所有相对时间显示
        function updateRelativeTimeDisplay() {
            // 更新同步记录表格中的时间
            const timeCells = document.querySelectorAll('[data-created-at]');
            timeCells.forEach(cell => {
                const createdAt = cell.getAttribute('data-created-at');
                if (createdAt) {
                    cell.textContent = getTimeAgo(createdAt);
                    cell.title = formatFullTime(createdAt);
                }
            });
        }
        
        // 配置管理功能
        function loadConfigs() {
            console.log('加载配置列表...');
            
            // 尝试新版API，失败则使用旧版API
            const apiEndpoints = [
                '/api/v1/sync/configs',  // 新版API
                '/api/sync/configs'      // 旧版API
            ];
            
            fetch(apiEndpoints[0])
                .then(response => {
                    console.log('配置API响应状态:', response.status);
                    if (!response.ok) {
                        console.warn('新版配置API失败，尝试旧版API');
                        return fetch(apiEndpoints[1]);
                    }
                    return response;
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('配置响应数据:', data);
                    
                    if (data.success) {
                        // 处理不同的数据结构
                        let configsData = [];
                        
                        if (data.data) {
                            if (Array.isArray(data.data)) {
                                configsData = data.data;
                            } else if (data.data.items) {
                                configsData = data.data.items; // 分页数据结构
                            }
                        } else if (Array.isArray(data.configs)) {
                            configsData = data.configs;
                        }
                        
                        // 调试：检查每个配置的ID字段
                        console.log('配置数据验证:');
                        configsData.forEach((config, index) => {
                            console.log(`配置 ${index}:`, {
                                id: config.id,
                                platform: config.platform,
                                document_id: config.document_id,
                                has_id: !!config.id,
                                id_type: typeof config.id
                            });
                        });
                        
                        updateConfigsTable(configsData);
                        console.log('配置列表加载完成，配置数:', configsData.length);
                    } else {
                        console.warn('配置列表加载失败:', data.message || data.error);
                        updateConfigsTable([]);
                        showNotification('加载同步配置失败', 'warning');
                    }
                })
                .catch(error => {
                    console.error('获取配置列表失败:', error);
                    updateConfigsTable([]);
                    showNotification('加载同步配置失败，请刷新重试', 'warning');
                });
        }
        
        // 触发配置立即同步
        function triggerConfigSync(documentId) {
            // 获取按钮并禁用
            const button = event.target.closest('button');
            if (button && button.disabled) return;
            
            if (button) {
                button.disabled = true;
                button.style.opacity = '0.6';
                button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>同步中...';
            }
            
            // 立即显示反馈
            showNotification('正在创建同步任务...', 'info');
            
            // 调用同步API
            fetch('/api/v1/sync/trigger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document_id: documentId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('同步任务已创建，正在后台处理', 'success');
                } else {
                    showNotification(data.message || data.error || '同步失败', 'error');
                }
            })
            .catch(error => {
                console.error('配置同步失败:', error);
                showNotification('网络错误，请重试', 'error');
            })
            .finally(() => {
                // 恢复按钮状态
                if (button) {
                    setTimeout(() => {
                        button.disabled = false;
                        button.style.opacity = '1';
                        button.innerHTML = '<i class="fas fa-sync mr-1"></i>立即同步';
                    }, 2000);
                }
            });
        }

        
        // 配置搜索功能
        function filterConfigs() {
            const searchTerm = document.getElementById('config-search').value.toLowerCase().trim();
            const configRows = document.querySelectorAll('.config-row');
            
            console.log('Search term:', searchTerm, 'Found rows:', configRows.length);
            
            configRows.forEach((row, index) => {
                const platform = row.dataset.platform || '';
                const documentId = row.dataset.documentId || '';
                const syncDirection = row.dataset.syncDirection || '';
                const status = row.dataset.status || '';
                
                console.log(`Row ${index}:`, { platform, documentId, syncDirection, status });
                
                // 检查搜索词是否匹配任何字段
                const matches = 
                    platform.includes(searchTerm) ||
                    documentId.includes(searchTerm) ||
                    syncDirection.includes(searchTerm) ||
                    status.includes(searchTerm) ||
                    (searchTerm === 'enabled' && status === 'enabled') ||
                    (searchTerm === 'disabled' && status === 'disabled') ||
                    (searchTerm === '已启用' && status === 'enabled') ||
                    (searchTerm === '已禁用' && status === 'disabled') ||
                    (searchTerm === 'feishu' && platform === 'feishu') ||
                    (searchTerm === 'notion' && platform === 'notion') ||
                    (searchTerm === '飞书' && platform === 'feishu');
                
                console.log(`Row ${index} matches:`, matches);
                
                // 显示或隐藏行
                row.style.display = matches || searchTerm === '' ? '' : 'none';
            });
            
            // 检查是否有可见的行
            const visibleRows = Array.from(configRows).filter(row => row.style.display !== 'none');
            const tbody = document.getElementById('configs-table-body');
            
            // 如果没有匹配的结果，显示"无搜索结果"
            const noResultsRow = tbody.querySelector('.no-results-row');
            if (visibleRows.length === 0 && searchTerm !== '') {
                if (!noResultsRow) {
                    const emptyRow = document.createElement('tr');
                    emptyRow.className = 'no-results-row';
                    emptyRow.innerHTML = `
                        <td colspan="5" class="px-6 py-8 text-center text-gray-500">
                            <i class="fas fa-search text-gray-300 text-2xl mb-2"></i>
                            <div>没有找到匹配 "${searchTerm}" 的配置</div>
                        </td>
                    `;
                    tbody.appendChild(emptyRow);
                }
            } else if (noResultsRow) {
                noResultsRow.remove();
            }
        }
        
        function updateConfigsTable(configs) {
            const tbody = document.getElementById('configs-table-body');
            if (!tbody) {
                console.warn('配置表格容器未找到');
                return;
            }
            
            tbody.innerHTML = '';
            
            // 确保configs是数组
            if (!Array.isArray(configs)) {
                configs = [];
            }
            
            // 调试信息：检查配置数据
            console.log('配置数据验证开始，总数:', configs.length);
            configs.forEach((config, index) => {
                console.log(`配置 ${index}:`, {
                    id: config.id,
                    platform: config.platform,
                    document_id: config.document_id,
                    has_id: !!config.id,
                    id_type: typeof config.id,
                    id_value: config.id
                });
            });
            
            if (configs.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="px-6 py-8 text-center text-gray-500">
                            <i class="fas fa-cog text-gray-300 text-2xl mb-2"></i>
                            <div>暂无同步配置</div>
                            <button onclick="showNewConfigModal()" class="mt-2 px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600">
                                创建配置
                            </button>
                        </td>
                    </tr>
                `;
                return;
            }
            
            configs.forEach(config => {
                // 添加调试信息
                console.log('配置数据:', config);
                console.log(`配置${config.id} is_sync_enabled 状态详情:`, {
                    original_value: config.is_sync_enabled,
                    type: typeof config.is_sync_enabled,
                    truthiness: !!config.is_sync_enabled,
                    should_show_as: config.is_sync_enabled ? '已启用' : '已禁用',
                    button_text: config.is_sync_enabled ? '禁用' : '启用'
                });
                
                // 检查必需字段
                if (!config.id) {
                    console.error('配置缺少ID字段:', config);
                    return;
                }
                
                // 确保所有必需字段都存在
                if (!config.platform || !config.document_id || !config.sync_direction) {
                    console.error('配置缺少必需字段:', config);
                    return;
                }
                
                const statusClass = config.is_sync_enabled ? 'status-running' : 'status-stopped';
                const statusText = config.is_sync_enabled ? '已启用' : '已禁用';
                const statusBgClass = config.is_sync_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800';
                
                const row = document.createElement('tr');
                row.className = 'table-row config-row';
                row.dataset.platform = (config.platform || '').toLowerCase();
                row.dataset.documentId = (config.document_id || '').toLowerCase();
                row.dataset.syncDirection = (config.sync_direction || '').toLowerCase();
                row.dataset.status = config.is_sync_enabled ? 'enabled' : 'disabled';
                
                // 数据验证：如果config.id不存在，跳过这个配置
                if (!config.id) {
                    console.error('配置缺少ID，跳过渲染:', config);
                    return;
                }
                
                // 为了避免undefined注入到HTML中，预处理数据
                const safeConfig = {
                    id: config.id,
                    platform: config.platform || 'unknown',
                    document_id: config.document_id || 'unknown',
                    sync_direction: config.sync_direction || 'unknown',
                    is_sync_enabled: !!config.is_sync_enabled,
                    created_at: config.created_at || new Date().toISOString()
                };
                
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center">
                            <div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                                <i class="fas fa-${safeConfig.platform === 'feishu' ? 'file-alt' : 'table'} text-blue-600"></i>
                            </div>
                            <div>
                                <div class="text-sm font-medium text-gray-900">${safeConfig.platform} 文档</div>
                                <div class="text-sm text-gray-500">ID: ${safeConfig.document_id.substring(0, 8)}...</div>
                            </div>
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center">
                            <span class="text-sm text-gray-900">${safeConfig.sync_direction}</span>
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusBgClass}">
                            <div class="status-indicator ${statusClass} mr-1"></div>
                            ${statusText}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${getTimeAgo(safeConfig.created_at)}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div class="flex items-center space-x-2">
                            ${safeConfig.is_sync_enabled ? 
                                `<button onclick="triggerConfigSync('${safeConfig.document_id}')" class="text-green-600 hover:text-green-900 font-medium" title="立即同步此配置">
                                    <i class="fas fa-sync mr-1"></i>立即同步
                                </button>` : ''}
                            <button onclick="editConfig('${safeConfig.id}')" class="text-blue-600 hover:text-blue-900">编辑</button>
                            <button onclick="toggleConfig('${safeConfig.id}', ${!safeConfig.is_sync_enabled})" class="text-yellow-600 hover:text-yellow-900">
                                ${safeConfig.is_sync_enabled ? '禁用' : '启用'}
                            </button>
                            <button onclick="deleteConfig('${safeConfig.id}')" class="text-red-600 hover:text-red-900">删除</button>
                        </div>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
        
        function updateDocumentsTable(documents) {
            const tbody = document.getElementById('documents-table-body');
            if (!tbody) {
                console.warn('文档表格容器未找到');
                return;
            }
            
            tbody.innerHTML = '';
            
            // 确保documents是数组
            if (!Array.isArray(documents)) {
                documents = [];
            }
            
            if (documents.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="px-6 py-8 text-center text-gray-500">
                            <i class="fas fa-folder-open text-gray-300 text-2xl mb-2"></i>
                            <div>文件夹中没有找到文档</div>
                        </td>
                    </tr>
                `;
                return;
            }
            
            documents.forEach((doc, index) => {
                const row = document.createElement('tr');
                row.className = 'hover:bg-gray-50';
                
                // 格式化文件大小
                let sizeText = '未知';
                if (doc.size && doc.size > 0) {
                    if (doc.size < 1024) {
                        sizeText = doc.size + ' B';
                    } else if (doc.size < 1024 * 1024) {
                        sizeText = Math.round(doc.size / 1024) + ' KB';
                    } else {
                        sizeText = Math.round(doc.size / (1024 * 1024) * 10) / 10 + ' MB';
                    }
                }
                
                // 格式化修改时间
                let timeText = '未知';
                if (doc.modified_time) {
                    try {
                        const date = new Date(doc.modified_time * 1000); // 假设是Unix时间戳
                        timeText = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                    } catch (e) {
                        timeText = doc.modified_time;
                    }
                }
                
                // 文档类型显示
                const typeText = doc.type || '未知';
                const typeClass = doc.type === 'docx' ? 'text-blue-600' : 
                                doc.type === 'sheet' ? 'text-green-600' : 
                                doc.type === 'bitable' ? 'text-purple-600' : 'text-gray-600';
                
                row.innerHTML = `
                    <td class="px-4 py-3">
                        <input type="checkbox" value="${doc.id || doc.token}" 
                               onchange="updateSelectedCount()" 
                               class="rounded border-gray-300 text-blue-600 focus:ring-blue-500">
                    </td>
                    <td class="px-6 py-4">
                        <div class="text-sm font-medium text-gray-900 truncate" title="${doc.name || '未命名文档'}">
                            ${doc.name || '未命名文档'}
                        </div>
                        <div class="text-xs text-gray-500">ID: ${doc.id || doc.token || 'unknown'}</div>
                    </td>
                    <td class="px-6 py-4">
                        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${typeClass} bg-gray-100">
                            ${typeText}
                        </span>
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-500">
                        ${sizeText}
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-500">
                        ${timeText}
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
        
        // 模态框显示/隐藏功能
        function showConfigModal() {
            document.getElementById('config-modal').classList.remove('hidden');
            
            // 加载Notion分类数据
            loadNotionCategories();
            
            // 监听同步方向改变
            const syncDirectionSelect = document.getElementById('config-sync-direction');
            syncDirectionSelect.addEventListener('change', toggleNotionCategorySection);
            
            // 初始化时检查是否需要显示分类选择
            toggleNotionCategorySection();
        }
        
        function hideConfigModal() {
            document.getElementById('config-modal').classList.add('hidden');
            document.getElementById('config-form').reset();
            
            // 重置为新增模式
            document.getElementById('config-modal-title').textContent = '新建同步配置';
            document.getElementById('config-submit-btn').textContent = '创建配置';
            window.currentEditingConfigId = null;
        }
        
        function showManualSyncModal() {
            document.getElementById('manual-sync-modal').classList.remove('hidden');
            
            // 加载Notion分类数据
            loadManualSyncNotionCategories();
            
            // 监听目标平台改变
            const targetPlatformSelect = document.getElementById('manual-target-platform');
            targetPlatformSelect.addEventListener('change', toggleManualNotionCategorySection);
            
            // 初始化时检查是否需要显示分类选择
            toggleManualNotionCategorySection();
        }
        
        function hideManualSyncModal() {
            document.getElementById('manual-sync-modal').classList.add('hidden');
            document.getElementById('manual-sync-input').value = '';
        }
        
        function showBatchSyncModal() {
            document.getElementById('batch-sync-modal').classList.remove('hidden');
        }
        
        function hideBatchSyncModal() {
            document.getElementById('batch-sync-modal').classList.add('hidden');
            document.getElementById('batch-folder-url').value = '';
        }
        
        // 文档选择模态框显示/隐藏
        function showDocumentSelectionModal(documents) {
            if (!documents || documents.length === 0) {
                showNotification('文件夹中没有找到文档', 'warning');
                return;
            }
            
            // 更新文档列表
            updateDocumentsTable(documents);
            
            // 显示模态框
            document.getElementById('document-selection-modal').classList.remove('hidden');
            
            // 重置选择状态
            const checkboxes = document.querySelectorAll('#documents-table-body input[type="checkbox"]');
            checkboxes.forEach(checkbox => checkbox.checked = false);
            document.getElementById('select-all-checkbox').checked = false;
            document.getElementById('selected-count').textContent = '已选择 0 个文档';
        }
        
        function hideDocumentSelectionModal() {
            document.getElementById('document-selection-modal').classList.add('hidden');
            // 清理选择状态
            const checkboxes = document.querySelectorAll('#documents-table-body input[type="checkbox"]');
            checkboxes.forEach(checkbox => checkbox.checked = false);
            document.getElementById('select-all-checkbox').checked = false;
            document.getElementById('selected-count').textContent = '已选择 0 个文档';
        }
        
        // 新建配置模态框显示/隐藏
        function showNewConfigModal() {
            document.getElementById('config-modal').classList.remove('hidden');
            // 重置表单
            document.getElementById('config-form').reset();
            document.getElementById('config-enabled').checked = true;
            document.getElementById('config-auto-sync').checked = false;
            window.currentEditingConfigId = null;
        }

        // 新建配置功能
        function submitConfigForm() {
            const platform = document.getElementById('config-platform').value;
            const documentId = document.getElementById('config-document-id').value;
            const syncDirection = document.getElementById('config-sync-direction').value;
            const enabled = document.getElementById('config-enabled').checked;
            const autoSync = document.getElementById('config-auto-sync').checked;
            const notionCategory = document.getElementById('config-notion-category').value;
            
            if (!documentId.trim()) {
                showNotification('请输入文档ID', 'error');
                return;
            }
            
            const configData = {
                platform: platform,
                document_id: documentId.trim(),
                sync_direction: syncDirection,
                is_sync_enabled: enabled,
                auto_sync: autoSync,
                notion_category: notionCategory || null
            };
            
            // 检查是否是编辑模式
            const isEditing = window.currentEditingConfigId;
            const url = isEditing ? `/api/v1/sync/configs/${window.currentEditingConfigId}` : '/api/v1/sync/config';
            const method = isEditing ? 'PATCH' : 'POST';
            const successMessage = isEditing ? '配置更新成功' : '配置创建成功';
            const errorMessage = isEditing ? '更新配置失败' : '创建配置失败';
            
            fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(configData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(successMessage, 'success');
                    hideConfigModal();
                    loadConfigs(); // 重新加载配置列表
                } else {
                    showNotification(data.message || errorMessage, 'error');
                }
            })
            .catch(error => {
                console.error('Error saving config:', error);
                showNotification(errorMessage, 'error');
            });
        }
        
        // 控制Notion分类选择区域的显示/隐藏
        function toggleNotionCategorySection() {
            const syncDirection = document.getElementById('config-sync-direction').value;
            const categorySection = document.getElementById('notion-category-section');
            
            if (syncDirection === 'feishu_to_notion' || syncDirection === 'bidirectional') {
                categorySection.classList.remove('hidden');
            } else {
                categorySection.classList.add('hidden');
            }
        }
        
        // 加载Notion分类数据
        function loadNotionCategories() {
            const categorySelect = document.getElementById('config-notion-category');
            
            // 清空现有选项
            categorySelect.innerHTML = '<option value="">选择分类...</option>';
            
            // 从API获取Notion分类
            fetch('/api/v1/notion/categories')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.categories) {
                        data.categories.forEach(category => {
                            const option = document.createElement('option');
                            option.value = category;
                            option.textContent = category;
                            categorySelect.appendChild(option);
                        });
                    } else {
                        // 如果获取失败，提供默认选项
                        const defaultCategories = ['技术分享', 'Post', 'Menu', '同步文档'];
                        defaultCategories.forEach(category => {
                            const option = document.createElement('option');
                            option.value = category;
                            option.textContent = category;
                            categorySelect.appendChild(option);
                        });
                    }
                })
                .catch(error => {
                    console.error('Failed to load Notion categories:', error);
                    // 提供默认选项
                    const defaultCategories = ['技术分享', 'Post', 'Menu', '同步文档'];
                    defaultCategories.forEach(category => {
                        const option = document.createElement('option');
                        option.value = category;
                        option.textContent = category;
                        categorySelect.appendChild(option);
                    });
                });
        }
        
        // 控制手动同步Notion分类选择区域的显示/隐藏
        function toggleManualNotionCategorySection() {
            const targetPlatform = document.getElementById('manual-target-platform').value;
            const categorySection = document.getElementById('manual-notion-category-section');
            
            if (targetPlatform === 'notion') {
                categorySection.classList.remove('hidden');
            } else {
                categorySection.classList.add('hidden');
            }
        }
        
        // 加载手动同步的Notion分类数据
        function loadManualSyncNotionCategories() {
            const categorySelect = document.getElementById('manual-notion-category');
            
            // 清空现有选项
            categorySelect.innerHTML = '<option value="">选择分类...</option>';
            
            // 从API获取Notion分类
            fetch('/api/v1/notion/categories')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.categories) {
                        data.categories.forEach(category => {
                            const option = document.createElement('option');
                            option.value = category;
                            option.textContent = category;
                            categorySelect.appendChild(option);
                        });
                    } else {
                        // 如果获取失败，提供默认选项
                        const defaultCategories = ['技术分享', 'Post', 'Menu', '同步文档'];
                        defaultCategories.forEach(category => {
                            const option = document.createElement('option');
                            option.value = category;
                            option.textContent = category;
                            categorySelect.appendChild(option);
                        });
                    }
                })
                .catch(error => {
                    console.error('Failed to load Notion categories for manual sync:', error);
                    // 提供默认选项
                    const defaultCategories = ['技术分享', 'Post', 'Menu', '同步文档'];
                    defaultCategories.forEach(category => {
                        const option = document.createElement('option');
                        option.value = category;
                        option.textContent = category;
                        categorySelect.appendChild(option);
                    });
                });
        }
        
        // 手动同步功能
        // 防重复执行的标志
        let isExecutingManualSync = false;
        
        function executeManualSync() {
            // 防止重复执行
            if (isExecutingManualSync) {
                console.log('手动同步正在执行中，忽略重复请求');
                return;
            }
            
            isExecutingManualSync = true;
            console.log('开始执行手动同步');
            
            const input = document.getElementById('manual-sync-input').value.trim();
            const sourcePlatform = document.getElementById('manual-source-platform').value;
            const targetPlatform = document.getElementById('manual-target-platform').value;
            const forceResync = document.getElementById('force-resync').checked;
            const notionCategory = document.getElementById('manual-notion-category').value;
            const notionType = document.getElementById('manual-notion-type').value;
            
            if (!input) {
                showNotification('请输入文档ID或链接', 'error');
                isExecutingManualSync = false;
                return;
            }
            
            // 支持多行输入，按行分割
            const lines = input.split('\n').filter(line => line.trim());
            
            if (lines.length === 0) {
                showNotification('请输入有效的文档ID或链接', 'error');
                isExecutingManualSync = false;
                return;
            }
            
            // 如果是链接，先解析ID
            const processInputs = lines.map(line => line.trim());
            
            // 判断是否包含链接，如果是则先解析
            const hasLinks = processInputs.some(input => input.includes('http'));
            
            if (hasLinks) {
                // 解析链接
                fetch('/api/v1/sync/parse-url', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ urls: processInputs })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.data.document_ids.length > 0) {
                        createManualSyncTasks(data.data.document_ids, sourcePlatform, targetPlatform, forceResync, notionCategory, notionType);
                    } else {
                        showNotification('链接解析失败', 'error');
                        // 重置执行标志
                        isExecutingManualSync = false;
                    }
                })
                .catch(error => {
                    console.error('Error parsing URLs:', error);
                    showNotification('链接解析失败', 'error');
                    // 重置执行标志
                    isExecutingManualSync = false;
                });
            } else {
                // 直接使用输入的ID
                createManualSyncTasks(processInputs, sourcePlatform, targetPlatform, forceResync, notionCategory, notionType);
            }
        }
        
        function createManualSyncTasks(documentIds, sourcePlatform, targetPlatform, forceResync = false, notionCategory = null, notionType = null) {
            fetch('/api/v1/sync/manual', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document_ids: documentIds,
                    source_platform: sourcePlatform,
                    target_platform: targetPlatform,
                    force_resync: forceResync,
                    notion_category: notionCategory,
                    notion_type: notionType
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('手动同步响应:', data); // 添加调试日志
                
                if (data.success) {
                    // 处理不同的响应数据结构
                    let message = '';
                    if (data.data && data.data.message) {
                        message = data.data.message;
                    } else if (data.message) {
                        message = data.message;
                    } else {
                        message = `成功创建 ${documentIds.length} 个手动同步任务`;
                    }
                    
                    showNotification(message, 'success');
                    hideManualSyncModal();
                    
                    // 清空输入框
                    document.getElementById('manual-sync-input').value = '';
                    
                    // 重置执行标志
                    isExecutingManualSync = false;
                    
                    // 延迟重新加载数据，确保同步任务已创建
                    setTimeout(() => {
                        loadSyncHistory(true); // 强制刷新同步历史
                        loadDashboardData(true); // 刷新仪表板数据
                    }, 500);
                } else {
                    const errorMessage = data.message || data.error || '创建同步任务失败';
                    showNotification(errorMessage, 'error');
                    console.error('手动同步失败:', data);
                    // 重置执行标志
                    isExecutingManualSync = false;
                }
            })
            .catch(error => {
                console.error('Error creating manual sync:', error);
                showNotification('创建同步任务失败，请检查网络连接', 'error');
                // 重置执行标志
                isExecutingManualSync = false;
            });
        }
        
        // 批量同步功能
        function previewFolderContents() {
            const folderUrl = document.getElementById('batch-folder-url').value.trim();
            const maxDepth = parseInt(document.getElementById('batch-max-depth').value);
            const useCache = document.getElementById('batch-use-cache').checked;
            
            if (!folderUrl) {
                showNotification('请输入文件夹链接', 'error');
                return;
            }
            
            showNotification('正在预览文件夹内容...', 'info');
            
            fetch('/api/v1/batch/folder/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    folder_path: folderUrl,
                    max_depth: maxDepth,
                    use_cache: useCache
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('文件夹内容预览完成', 'success');
                    // 显示文档选择弹窗
                    showDocumentSelectionModal(data.data.documents);
                } else {
                    // 处理不同类型的错误
                    let errorMsg = data.error?.message || data.message || '预览文件夹内容失败';
                    
                    if (data.error?.code === 'FEISHU_CONFIG_MISSING') {
                        errorMsg += '\n\n请联系系统管理员配置飞书API密钥';
                        if (data.error?.details?.missing_configs) {
                            errorMsg += '\n缺少配置: ' + data.error.details.missing_configs.join(', ');
                        }
                    } else if (data.error?.code === 'PERMISSION_DENIED') {
                        errorMsg += '\n\n请检查：\n1. 文件夹链接是否正确\n2. 飞书应用是否有权限访问该文件夹\n3. 联系文件夹管理员授权';
                    } else if (data.error?.code === 'AUTHENTICATION_FAILED') {
                        errorMsg += '\n\n请联系系统管理员检查飞书API配置';
                    } else if (data.error?.code === 'FOLDER_NOT_FOUND') {
                        errorMsg += '\n\n请检查文件夹链接是否正确';
                    } else if (data.error?.code === 'RATE_LIMIT') {
                        errorMsg += '\n\n请稍后重试，或启用缓存模式';
                    }
                    
                    showNotification(errorMsg, 'error');
                    console.error('API Error:', data.error);
                }
            })
            .catch(error => {
                console.error('Error previewing folder:', error);
                showNotification('预览文件夹内容失败', 'error');
            });
        }
        
        function executeBatchSync() {
            const folderUrl = document.getElementById('batch-folder-url').value.trim();
            const maxDepth = parseInt(document.getElementById('batch-max-depth').value);
            const useCache = document.getElementById('batch-use-cache').checked;
            
            if (!folderUrl) {
                showNotification('请输入文件夹链接', 'error');
                return;
            }
            
            showNotification('正在扫描文件夹并创建同步任务...', 'info');
            
            // 先扫描文件夹获取文档列表
            fetch('/api/v1/batch/folder/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    folder_path: folderUrl,
                    max_depth: maxDepth,
                    use_cache: useCache
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('文件夹扫描结果:', data);
                
                if (data.success) {
                    if (data.documents && data.documents.length > 0) {
                        // 提取文档ID列表
                        const documentIds = data.documents.map(doc => doc.token);
                        console.log('提取的文档ID:', documentIds);
                        
                        // 创建批量同步任务
                        return fetch('/api/v1/sync/batch', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                document_ids: documentIds,
                                force_sync: true
                            })
                        });
                    } else {
                        let errorMsg = `文件夹中没有可同步的文档（找到 ${data.total_documents || 0} 个文档）`;
                        if (data.scan_stats && data.scan_stats.file_types) {
                            const fileTypes = Object.entries(data.scan_stats.file_types)
                                .map(([type, count]) => `${type}(${count}个)`)
                                .join(', ');
                            errorMsg += `。发现的文件类型: ${fileTypes}`;
                        }
                        if (data.scan_summary) {
                            errorMsg += `。${data.scan_summary}`;
                        }
                        throw new Error(errorMsg);
                    }
                } else {
                    throw new Error(data.message || '文件夹扫描失败');
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(data.message || '批量同步任务已创建', 'success');
                    hideBatchSyncModal();
                    loadSyncHistory(); // 重新加载同步历史
                } else {
                    showNotification(data.message || '批量同步失败', 'error');
                }
            })
            .catch(error => {
                console.error('Error executing batch sync:', error);
                if (error.message) {
                    showNotification(error.message, 'error');
                } else {
                    showNotification('批量同步失败', 'error');
                }
            });
        }
        
        function editConfig(configId) {
            console.log('editConfig called with:', configId);
            
            // 验证参数
            if (!configId || configId === 'undefined' || configId === 'null' || configId === '' || configId === 'unknown') {
                console.error('无效的配置ID:', configId);
                showNotification('配置ID无效，无法编辑', 'error');
                return;
            }
            
            // 获取配置详情
            fetch(`/api/v1/sync/config/${configId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showEditConfigModal(data.data);
                    } else {
                        showNotification('获取配置详情失败', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error loading config:', error);
                    showNotification('获取配置详情失败', 'error');
                });
        }
        
        function showEditConfigModal(config) {
            // 填充表单数据
            document.getElementById('config-platform').value = config.platform;
            document.getElementById('config-document-id').value = config.document_id;
            document.getElementById('config-sync-direction').value = config.sync_direction;
            document.getElementById('config-enabled').checked = config.is_sync_enabled;
            document.getElementById('config-auto-sync').checked = config.auto_sync;
            
            // 设置模态框为编辑模式
            document.getElementById('config-modal-title').textContent = '编辑同步配置';
            document.getElementById('config-submit-btn').textContent = '更新配置';
            
            // 存储当前编辑的配置ID
            window.currentEditingConfigId = config.id;
            
            // 显示模态框
            document.getElementById('config-modal').classList.remove('hidden');
        }
        
        function toggleConfig(configId, enable) {
            console.log('toggleConfig 详细调试信息:', { 
                configId, 
                enable, 
                configId_type: typeof configId,
                enable_type: typeof enable,
                configId_value: configId,
                enable_value: enable,
                arguments_length: arguments.length,
                all_arguments: Array.from(arguments)
            });
            
            // 验证参数
            if (!configId || configId === 'undefined' || configId === 'null' || configId === '' || configId === 'unknown') {
                console.error('无效的配置ID:', configId);
                console.error('完整参数信息:', { configId, enable, arguments: Array.from(arguments) });
                showNotification('配置ID无效，无法切换状态', 'error');
                return;
            }
            
            fetch(`/api/v1/sync/config/${configId}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    enabled: enable
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Toggle API 响应数据:', data);
                if (data.success) {
                    const successMessage = data.data?.message || data.message || '配置切换成功';
                    showNotification(successMessage, 'success');
                    loadConfigs(); // 重新加载配置列表
                } else {
                    const errorMessage = data.data?.message || data.message || '配置切换失败';
                    showNotification(errorMessage, 'error');
                }
            })
            .catch(error => {
                console.error('Error toggling config:', error);
                showNotification('操作失败', 'error');
            });
        }
        
        function deleteConfig(configId) {
            console.log('删除配置，ID:', configId);
            
            // 检查配置ID是否有效
            if (!configId || configId === 'undefined' || configId === 'null' || configId === '' || configId === 'unknown') {
                console.error('无效的配置ID:', configId);
                showNotification('配置ID无效，无法删除', 'error');
                return;
            }
            
            if (confirm('确定要删除这个配置吗？')) {
                showNotification('正在删除配置...', 'info');
                
                fetch(`/api/v1/sync/config/${configId}`, {
                    method: 'DELETE'
                })
                .then(response => {
                    console.log('删除响应状态:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('删除响应数据:', data);
                    if (data.success) {
                        showNotification(data.message || '配置删除成功', 'success');
                        loadConfigs(); // 重新加载配置列表
                    } else {
                        showNotification(data.message || '删除失败', 'error');
                    }
                })
                .catch(error => {
                    console.error('删除配置错误:', error);
                    showNotification('删除失败: ' + error.message, 'error');
                });
            }
        }

        // 初始化所有事件监听器
        function initEventListeners() {
            
            // 移动端侧边栏控制
            const mobileMenuBtn = document.getElementById('mobile-menu-btn');
            const sidebar = document.getElementById('sidebar');
            
            if (mobileMenuBtn && sidebar) {
                mobileMenuBtn.addEventListener('click', () => {
                    sidebar.classList.toggle('open');
                });
                
                // 点击主内容区域时关闭侧边栏
                document.addEventListener('click', (e) => {
                    if (window.innerWidth <= 768 && !sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
                        sidebar.classList.remove('open');
                    }
                });
            }
            

            // 配置相关按钮
            const showConfigModalBtns = document.querySelectorAll('button[onclick*="showConfigModal"]');
            showConfigModalBtns.forEach(btn => {
                btn.removeAttribute('onclick');
                btn.addEventListener('click', showConfigModal);
            });

            // 同步相关按钮
            const showManualSyncModalBtns = document.querySelectorAll('button[onclick*="showManualSyncModal"]');
            showManualSyncModalBtns.forEach(btn => {
                btn.removeAttribute('onclick');
                btn.addEventListener('click', showManualSyncModal);
            });

            const showBatchSyncModalBtns = document.querySelectorAll('button[onclick*="showBatchSyncModal"]');
            showBatchSyncModalBtns.forEach(btn => {
                btn.removeAttribute('onclick');
                btn.addEventListener('click', showBatchSyncModal);
            });

            // 刷新按钮
            const refreshDashboardBtns = document.querySelectorAll('button[onclick*="loadDashboardData"]');
            refreshDashboardBtns.forEach(btn => {
                btn.removeAttribute('onclick');
                btn.addEventListener('click', () => {
                    loadDashboardData();
                    loadSyncHistory();
                });
            });

            const refreshMonitoringBtns = document.querySelectorAll('button[onclick*="refreshMonitoringData"]');
            refreshMonitoringBtns.forEach(btn => {
                btn.removeAttribute('onclick');
                btn.addEventListener('click', refreshMonitoringData);
            });

            const refreshDataViewBtns = document.querySelectorAll('button[onclick*="refreshDataView"]');
            refreshDataViewBtns.forEach(btn => {
                btn.removeAttribute('onclick');
                btn.addEventListener('click', refreshDataView);
            });

            // 分页大小选择事件将由initDataPagePagination()处理

            // 全局刷新按钮
            const refreshAllDataBtns = document.querySelectorAll('button[onclick*="refreshAllData"]');
            refreshAllDataBtns.forEach(btn => {
                btn.removeAttribute('onclick');
                btn.addEventListener('click', refreshAllData);
            });

            // 数据管理按钮
            const batchRetryBtns = document.querySelectorAll('button[onclick*="batchRetryRecords"]');
            batchRetryBtns.forEach(btn => {
                const onclick = btn.getAttribute('onclick');
                const match = onclick.match(/batchRetryRecords\('([^']+)'\)/);
                if (match) {
                    const status = match[1];
                    btn.removeAttribute('onclick');
                    btn.addEventListener('click', () => batchRetryRecords(status));
                }
            });

            // 删除操作按钮
            const deleteFailedBtn = document.querySelector('button[onclick*="deleteFailedRecords"]');
            if (deleteFailedBtn) {
                deleteFailedBtn.removeAttribute('onclick');
                deleteFailedBtn.addEventListener('click', deleteFailedRecords);
            }

            const deleteProcessingBtn = document.querySelector('button[onclick*="deleteProcessingRecords"]');
            if (deleteProcessingBtn) {
                deleteProcessingBtn.removeAttribute('onclick');
                deleteProcessingBtn.addEventListener('click', deleteProcessingRecords);
            }

            const deleteAllBtn = document.querySelector('button[onclick*="deleteAllRecords"]');
            if (deleteAllBtn) {
                deleteAllBtn.removeAttribute('onclick');
                deleteAllBtn.addEventListener('click', deleteAllRecords);
            }

            // 分页按钮 - 这部分将由initDataPagePagination()处理，删除重复绑定
            // const prevPageBtn = document.getElementById('prev-page');
            // const nextPageBtn = document.getElementById('next-page');
            // if (prevPageBtn) {
            //     prevPageBtn.removeAttribute('onclick');
            //     prevPageBtn.addEventListener('click', () => changePage(-1));
            // }
            // if (nextPageBtn) {
            //     nextPageBtn.removeAttribute('onclick');
            //     nextPageBtn.addEventListener('click', () => changePage(1));
            // }

            // 连接测试按钮
            const testFeishuBtn = document.querySelector('button[onclick*="testFeishuConnection"]');
            if (testFeishuBtn) {
                testFeishuBtn.removeAttribute('onclick');
                testFeishuBtn.addEventListener('click', testFeishuConnection);
            }

            const testNotionBtn = document.querySelector('button[onclick*="testNotionConnection"]');
            if (testNotionBtn) {
                testNotionBtn.removeAttribute('onclick');
                testNotionBtn.addEventListener('click', testNotionConnection);
            }

            const testQiniuBtn = document.querySelector('button[onclick*="testQiniuConnection"]');
            if (testQiniuBtn) {
                testQiniuBtn.removeAttribute('onclick');
                testQiniuBtn.addEventListener('click', testQiniuConnection);
            }

            // 系统设置按钮
            const saveSettingsBtn = document.querySelector('button[onclick*="saveSystemSettings"]');
            if (saveSettingsBtn) {
                saveSettingsBtn.removeAttribute('onclick');
                saveSettingsBtn.addEventListener('click', saveSystemSettings);
            }

            // 帮助页面按钮
            const helpTabBtns = document.querySelectorAll('button[onclick*="switchHelpTab"]');
            helpTabBtns.forEach(btn => {
                const onclick = btn.getAttribute('onclick');
                const match = onclick.match(/switchHelpTab\('([^']+)'\)/);
                if (match) {
                    const tab = match[1];
                    btn.removeAttribute('onclick');
                    btn.addEventListener('click', () => switchHelpTab(tab));
                }
            });

            // 导航相关按钮
            const quickActionBtns = document.querySelectorAll('button[onclick*="showPage"]');
            quickActionBtns.forEach(btn => {
                const onclick = btn.getAttribute('onclick');
                const match = onclick.match(/showPage\('([^']+)'\)/);
                if (match) {
                    const page = match[1];
                    btn.removeAttribute('onclick');
                    btn.addEventListener('click', () => showPage(page));
                }
            });


            const showVersionInfoBtn = document.querySelector('button[onclick*="showVersionInfo"]');
            if (showVersionInfoBtn) {
                showVersionInfoBtn.removeAttribute('onclick');
                showVersionInfoBtn.addEventListener('click', showVersionInfo);
            }

            const hideVersionsFloatingBallBtn = document.querySelector('button[onclick*="hideVersionsFloatingBall"]');
            if (hideVersionsFloatingBallBtn) {
                hideVersionsFloatingBallBtn.removeAttribute('onclick');
                hideVersionsFloatingBallBtn.addEventListener('click', hideVersionsFloatingBall);
            }

            // 为弹窗内的按钮添加事件监听器
            // 使用延迟绑定来确保DOM完全加载
            setTimeout(() => {
                // 手动同步弹窗的按钮
                const manualSyncButtons = document.querySelectorAll('#manual-sync-modal button');
                manualSyncButtons.forEach(btn => {
                    const text = btn.textContent.trim();
                    if (text.includes('立即执行同步')) {
                        // 移除可能存在的旧事件监听器
                        btn.removeEventListener('click', executeManualSync);
                        btn.addEventListener('click', executeManualSync);
                    } else if (text.includes('取消')) {
                        btn.removeEventListener('click', hideManualSyncModal);
                        btn.addEventListener('click', hideManualSyncModal);
                    }
                });

                // 批量同步弹窗的按钮
                const batchSyncButtons = document.querySelectorAll('#batch-sync-modal button');
                batchSyncButtons.forEach(btn => {
                    const text = btn.textContent.trim();
                    if (text.includes('预览内容')) {
                        btn.addEventListener('click', previewFolderContents);
                    } else if (text.includes('批量同步')) {
                        btn.addEventListener('click', executeBatchSync);
                    } else if (text.includes('取消')) {
                        btn.addEventListener('click', hideBatchSyncModal);
                    }
                });

                // 新建配置弹窗的按钮
                const configButtons = document.querySelectorAll('#config-modal button');
                configButtons.forEach(btn => {
                    const text = btn.textContent.trim();
                    if (text.includes('取消')) {
                        btn.addEventListener('click', hideConfigModal);
                    }
                    // 提交按钮已经通过form的onsubmit处理
                });

                // 文档选择弹窗的按钮
                const documentSelectionButtons = document.querySelectorAll('#document-selection-modal button');
                documentSelectionButtons.forEach(btn => {
                    const text = btn.textContent.trim();
                    if (text.includes('取消')) {
                        btn.addEventListener('click', hideDocumentSelectionModal);
                    } else if (text.includes('同步选中文档')) {
                        btn.addEventListener('click', executeSelectedSync);
                    } else if (text.includes('全选')) {
                        btn.addEventListener('click', selectAllDocuments);
                    } else if (text.includes('取消全选')) {
                        btn.addEventListener('click', selectNoneDocuments);
                    }
                });
            }, 100);
        }

        // 页面加载完成后初始化所有功能
        document.addEventListener('DOMContentLoaded', function() {
            console.log('页面加载完成，初始化应用...');
            
            // 初始化导航功能
            initNavigation();
            
            // 初始化事件监听器
            initEventListeners();
            
            // 初始化弹窗功能
            initModalFeatures();
            
            // 加载默认页面数据
            showPage('dashboard');
            
            console.log('应用初始化完成');
        });

        // 初始化弹窗功能
        function initModalFeatures() {
            // 添加弹窗关闭按钮的事件监听器
            const modalCloseButtons = document.querySelectorAll('.text-gray-400[class*="hover:text-gray-600"]');
            modalCloseButtons.forEach(btn => {
                btn.addEventListener('click', function() {
                    const modal = this.closest('.fixed');
                    if (modal) {
                        modal.classList.add('hidden');
                        // 根据弹窗ID执行特定的清理
                        if (modal.id === 'config-modal') {
                            hideConfigModal();
                        } else if (modal.id === 'manual-sync-modal') {
                            hideManualSyncModal();
                        } else if (modal.id === 'batch-sync-modal') {
                            hideBatchSyncModal();
                        } else if (modal.id === 'document-selection-modal') {
                            hideDocumentSelectionModal();
                        }
                    }
                });
            });

            // 添加弹窗背景点击关闭功能
            const modals = ['config-modal', 'manual-sync-modal', 'batch-sync-modal', 'document-selection-modal'];
            modals.forEach(modalId => {
                const modal = document.getElementById(modalId);
                if (modal) {
                    modal.addEventListener('click', function(e) {
                        if (e.target === this) {
                            if (modalId === 'config-modal') {
                                hideConfigModal();
                            } else if (modalId === 'manual-sync-modal') {
                                hideManualSyncModal();
                            } else if (modalId === 'batch-sync-modal') {
                                hideBatchSyncModal();
                            } else if (modalId === 'document-selection-modal') {
                                hideDocumentSelectionModal();
                            }
                        }
                    });
                }
            });

            // 添加ESC键关闭弹窗功能
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    const configModal = document.getElementById('config-modal');
                    const manualSyncModal = document.getElementById('manual-sync-modal');
                    const batchSyncModal = document.getElementById('batch-sync-modal');
                    const documentSelectionModal = document.getElementById('document-selection-modal');
                    
                    // 检查哪个弹窗是打开的，然后关闭它
                    if (configModal && !configModal.classList.contains('hidden')) {
                        hideConfigModal();
                    } else if (manualSyncModal && !manualSyncModal.classList.contains('hidden')) {
                        hideManualSyncModal();
                    } else if (batchSyncModal && !batchSyncModal.classList.contains('hidden')) {
                        hideBatchSyncModal();
                    } else if (documentSelectionModal && !documentSelectionModal.classList.contains('hidden')) {
                        hideDocumentSelectionModal();
                    }
                }
            });
        }

        // 通知函数
        function showNotification(message, type = 'info') {
            // 创建通知元素
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                padding: 12px 20px;
                border-radius: 8px;
                color: white;
                font-weight: 500;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transform: translateX(100%);
                transition: transform 0.3s ease;
                max-width: 300px;
                word-wrap: break-word;
            `;
            
            // 根据类型设置背景色
            switch(type) {
                case 'success':
                    notification.style.backgroundColor = '#10b981';
                    break;
                case 'error':
                    notification.style.backgroundColor = '#ef4444';
                    break;
                case 'warning':
                    notification.style.backgroundColor = '#f59e0b';
                    break;
                default:
                    notification.style.backgroundColor = '#3b82f6';
            }
            
            notification.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <span>${message}</span>
                    <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: white; margin-left: 10px; cursor: pointer; font-size: 18px;">&times;</button>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // 显示动画
            setTimeout(() => {
                notification.style.transform = 'translateX(0)';
            }, 100);
            
            // 自动消失
            setTimeout(() => {
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 300);
            }, 3000);
        }

        // 刷新所有数据
        function refreshAllData() {
            console.log('刷新所有数据被调用');
            
            // 显示加载提示
            showNotification('正在刷新数据...', 'info');
            
            // 清理缓存
            invalidateCache('dashboard');
            invalidateCache('configs');
            invalidateCache('history');
            
            // 根据当前页面刷新对应数据
            const refreshPromises = [];
            
            try {
                // 基础数据刷新
                refreshPromises.push(loadProcessorStatus());
                
                if (currentPage === 'dashboard') {
                    refreshPromises.push(
                        loadDashboardData(true),
                        loadSyncHistory(true)
                    );
                } else if (currentPage === 'configs') {
                    refreshPromises.push(loadConfigs());
                } else if (currentPage === 'monitoring') {
                    // 监控页面的刷新
                    if (typeof refreshMonitoringData === 'function') {
                        refreshPromises.push(refreshMonitoringData());
                    }
                } else if (currentPage === 'data') {
                    // 数据管理页面的刷新
                    if (typeof refreshDataView === 'function') {
                        refreshPromises.push(refreshDataView());
                    }
                } else {
                    // 默认刷新基础数据
                    refreshPromises.push(
                        loadDashboardData(true),
                        loadSyncHistory(true)
                    );
                }
                
                // 执行所有刷新操作
                Promise.all(refreshPromises)
                    .then(() => {
                        showNotification('数据刷新完成', 'success');
                        console.log('所有数据刷新完成');
                    })
                    .catch(error => {
                        console.error('刷新数据失败:', error);
                        showNotification('部分数据刷新失败，请重试', 'warning');
                    });
                    
            } catch (error) {
                console.error('刷新数据出错:', error);
                showNotification('刷新失败，请重试', 'error');
            }
        }

        // 最近活动相关函数
        function loadRecentActivities(limit = 10) {
            console.log('加载最近活动...');
            
            const loadingElement = document.getElementById('recent-activities-loading');
            const listElement = document.getElementById('recent-activities-list');
            const emptyElement = document.getElementById('recent-activities-empty');
            
            // 显示加载状态
            if (loadingElement) loadingElement.classList.remove('hidden');
            if (listElement) listElement.classList.add('hidden');
            if (emptyElement) emptyElement.classList.add('hidden');
            
            return fetch(`/api/v1/recent-activities?limit=${limit}&_=${Date.now()}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        renderRecentActivities(data.data);
                        console.log('最近活动加载完成');
                    } else {
                        console.warn('最近活动加载失败:', data.message);
                        showRecentActivitiesEmpty();
                    }
                })
                .catch(error => {
                    console.error('获取最近活动失败:', error);
                    showRecentActivitiesEmpty();
                })
                .finally(() => {
                    // 隐藏加载状态
                    if (loadingElement) loadingElement.classList.add('hidden');
                });
        }

        function renderRecentActivities(activities) {
            const listElement = document.getElementById('recent-activities-list');
            const emptyElement = document.getElementById('recent-activities-empty');
            
            if (!listElement) return;
            
            if (!activities || activities.length === 0) {
                showRecentActivitiesEmpty();
                return;
            }
            
            // 生成活动列表HTML
            const activitiesHtml = activities.map((activity, index) => {
                const isLast = index === activities.length - 1;
                return `
                    <li>
                        <div class="relative ${isLast ? '' : 'pb-8'}">
                            ${isLast ? '' : '<span class="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"></span>'}
                            <div class="relative flex space-x-3">
                                <div>
                                    <span class="h-8 w-8 rounded-full ${activity.icon_color} flex items-center justify-center ring-8 ring-white">
                                        <i class="${activity.icon_class} text-white text-sm"></i>
                                    </span>
                                </div>
                                <div class="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                                    <div>
                                        <p class="text-sm text-gray-500">
                                            ${activity.activity_text}
                                        </p>
                                        ${activity.record_number ? `<p class="text-xs text-gray-400 mt-1">记录编号: ${activity.record_number}</p>` : ''}
                                    </div>
                                    <div class="text-right text-sm whitespace-nowrap text-gray-500">
                                        ${activity.time_ago}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </li>
                `;
            }).join('');
            
            listElement.innerHTML = activitiesHtml;
            listElement.classList.remove('hidden');
            if (emptyElement) emptyElement.classList.add('hidden');
        }

        function showRecentActivitiesEmpty() {
            const listElement = document.getElementById('recent-activities-list');
            const emptyElement = document.getElementById('recent-activities-empty');
            
            if (listElement) listElement.classList.add('hidden');
            if (emptyElement) emptyElement.classList.remove('hidden');
        }

        function refreshRecentActivities() {
            console.log('刷新最近活动');
            loadRecentActivities();
        }

        // 添加缺失的函数定义
        
        // 文档选择相关函数
        function selectAllDocuments() {
            // 只选择可见的文档
            const visibleRows = Array.from(document.querySelectorAll('#documents-table-body tr')).filter(row => row.style.display !== 'none');
            const visibleCheckboxes = visibleRows.map(row => row.querySelector('input[type="checkbox"]')).filter(cb => cb);
            
            visibleCheckboxes.forEach(checkbox => checkbox.checked = true);
            updateSelectedCount();
        }

        function selectNoneDocuments() {
            // 只取消选择可见的文档
            const visibleRows = Array.from(document.querySelectorAll('#documents-table-body tr')).filter(row => row.style.display !== 'none');
            const visibleCheckboxes = visibleRows.map(row => row.querySelector('input[type="checkbox"]')).filter(cb => cb);
            
            visibleCheckboxes.forEach(checkbox => checkbox.checked = false);
            updateSelectedCount();
        }

        function updateSelectedCount() {
            // 只计算可见的复选框
            const visibleRows = Array.from(document.querySelectorAll('#documents-table-body tr')).filter(row => row.style.display !== 'none');
            const visibleCheckboxes = visibleRows.map(row => row.querySelector('input[type="checkbox"]')).filter(cb => cb);
            const checkedVisibleCheckboxes = visibleCheckboxes.filter(cb => cb.checked);
            
            const count = checkedVisibleCheckboxes.length;
            const totalVisible = visibleCheckboxes.length;
            
            const countElement = document.getElementById('selected-count');
            if (countElement) {
                countElement.textContent = `已选择 ${count} 个文档`;
            }
            
            // 更新全选复选框状态（基于可见的复选框）
            const selectAllCheckbox = document.getElementById('select-all-checkbox');
            if (selectAllCheckbox && totalVisible > 0) {
                selectAllCheckbox.checked = count === totalVisible;
                selectAllCheckbox.indeterminate = count > 0 && count < totalVisible;
            }
        }
        
        function toggleAllDocuments() {
            const selectAllCheckbox = document.getElementById('select-all-checkbox');
            
            if (selectAllCheckbox) {
                const shouldCheck = selectAllCheckbox.checked;
                
                // 只处理可见的文档
                const visibleRows = Array.from(document.querySelectorAll('#documents-table-body tr')).filter(row => row.style.display !== 'none');
                const visibleCheckboxes = visibleRows.map(row => row.querySelector('input[type="checkbox"]')).filter(cb => cb);
                
                visibleCheckboxes.forEach(checkbox => {
                    checkbox.checked = shouldCheck;
                });
                updateSelectedCount();
            }
        }

        function executeSelectedSync() {
            const selectedCheckboxes = document.querySelectorAll('#documents-table-body input[type="checkbox"]:checked');
            const documentIds = Array.from(selectedCheckboxes).map(checkbox => checkbox.value);
            
            if (documentIds.length === 0) {
                showNotification('请选择要同步的文档', 'warning');
                return;
            }

            // 执行选中文档的同步
            createManualSyncTasks(documentIds, 'feishu', 'notion', false);
            hideDocumentSelectionModal();
        }
        
        function filterDocuments() {
            const searchInput = document.getElementById('document-search');
            const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
            const rows = document.querySelectorAll('#documents-table-body tr');
            
            rows.forEach(row => {
                // 获取文档名称单元格
                const nameCell = row.querySelector('td:nth-child(2) div');
                const documentName = nameCell ? nameCell.textContent.toLowerCase() : '';
                
                // 显示或隐藏行
                if (documentName.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
            
            // 更新选择计数
            updateSelectedCount();
        }

        // 监控相关函数（如果不存在）
        function refreshMonitoringData() {
            console.log('刷新监控数据');
            
            // 刷新监控页面的所有数据
            const refreshPromises = [
                loadProcessorStatus(),
                loadMonitoringSyncRecords()
            ];
            
            return Promise.all(refreshPromises)
                .then(() => {
                    console.log('监控数据刷新完成');
                })
                .catch(error => {
                    console.error('监控数据刷新失败:', error);
                    throw error;
                });
        }

        function refreshDataView() {
            console.log('刷新数据视图');
            
            // 根据当前选择的视图类型加载数据
            const viewTypeElement = document.getElementById('data-view-type');
            console.log('数据视图类型元素:', viewTypeElement);
            const viewType = viewTypeElement?.value || 'all';
            console.log('当前视图类型:', viewType);
            
            if (viewType === 'images') {
                // 如果是图片管理视图
                console.log('加载图片管理视图...');
                loadImageStats();
                loadImagesList();
            } else {
                // 如果是同步记录视图，使用数据统计
                console.log('加载同步记录视图...');
                try {
                    loadDataStats();
                    loadDataPageRecords();
                } catch (error) {
                    console.error('数据视图加载失败:', error);
                    // 显示友好的错误消息而不是保持加载状态
                    showNotification('数据加载完成，部分组件可能不可见', 'info');
                }
            }
            
            console.log('数据视图刷新完成');
        }

        // 新增：加载数据管理页面的统计数据
        function loadDataStats() {
            console.log('加载数据统计信息...');
            
            const statsContainer = document.getElementById('data-stats');
            console.log('统计数据容器:', statsContainer);
            if (!statsContainer) {
                console.warn('数据统计容器未找到，尝试查找监控页面的统计容器');
                // 尝试查找监控页面的统计容器作为fallback
                const monitoringStatsContainer = document.querySelector('#monitoring-stats, .monitoring-stats, .dashboard-stats');
                console.log('fallback统计容器:', monitoringStatsContainer);
                if (!monitoringStatsContainer) {
                    console.warn('未找到任何统计容器，跳过数据统计加载');
                    return Promise.resolve();
                }
                // 使用监控页面的容器
                return loadDataStatsToContainer(monitoringStatsContainer);
            }
            
            return loadDataStatsToContainer(statsContainer);
        }

        function loadDataStatsToContainer(container) {
            // 显示加载状态
            container.innerHTML = `
                <div class="loading-spinner inline-block mr-2"></div>
                <span>加载统计数据...</span>
            `;
            
            return fetch('/api/v1/dashboard?_=' + Date.now())
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('数据统计响应:', data);
                    
                    if (data.success) {
                        updateDataStatsDisplayInContainer(data.data, container);
                    } else {
                        throw new Error(data.message || '获取统计数据失败');
                    }
                })
                .catch(error => {
                    console.error('获取数据统计失败:', error);
                    container.innerHTML = `
                        <div class="text-red-600">
                            <i class="fas fa-exclamation-triangle mr-2"></i>
                            <span>加载统计数据失败: ${error.message}</span>
                        </div>
                    `;
                });
        }

        // 新增：更新数据统计显示
        function updateDataStatsDisplay(stats) {
            const statsContainer = document.getElementById('data-stats');
            if (!statsContainer) return;
            updateDataStatsDisplayInContainer(stats, statsContainer);
        }

        function updateDataStatsDisplayInContainer(stats, container) {
            
            const successRate = stats.success_rate || 0;
            const totalRecords = stats.total_records || 0;
            const successRecords = stats.success_records || 0;
            const failedRecords = stats.failed_records || 0;
            const pendingRecords = stats.pending_records || 0;
            const totalConfigs = stats.total_configs || 0;
            const activeConfigs = stats.active_configs || 0;
            
            container.innerHTML = `
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <!-- 同步记录统计 -->
                    <div class="text-center p-4 bg-blue-50 rounded-lg">
                        <div class="text-2xl font-bold text-blue-600">${totalRecords}</div>
                        <div class="text-sm text-blue-700">总同步记录</div>
                    </div>
                    
                    <!-- 成功率统计 -->
                    <div class="text-center p-4 bg-green-50 rounded-lg">
                        <div class="text-2xl font-bold text-green-600">${successRate.toFixed(1)}%</div>
                        <div class="text-sm text-green-700">同步成功率</div>
                    </div>
                    
                    <!-- 配置统计 -->
                    <div class="text-center p-4 bg-purple-50 rounded-lg">
                        <div class="text-2xl font-bold text-purple-600">${activeConfigs}/${totalConfigs}</div>
                        <div class="text-sm text-purple-700">启用配置</div>
                    </div>
                    
                    <!-- 待处理任务 -->
                    <div class="text-center p-4 bg-orange-50 rounded-lg">
                        <div class="text-2xl font-bold text-orange-600">${pendingRecords}</div>
                        <div class="text-sm text-orange-700">待处理任务</div>
                    </div>
                </div>
                
                <!-- 详细统计 -->
                <div class="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="bg-white border border-gray-200 rounded-lg p-4">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-sm font-medium text-gray-500">成功记录</div>
                                <div class="text-xl font-bold text-green-600">${successRecords}</div>
                            </div>
                            <div class="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                                <i class="fas fa-check-circle text-green-600"></i>
                            </div>
                        </div>
                    </div>
                    
                    <div class="bg-white border border-gray-200 rounded-lg p-4">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-sm font-medium text-gray-500">失败记录</div>
                                <div class="text-xl font-bold text-red-600">${failedRecords}</div>
                            </div>
                            <div class="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                                <i class="fas fa-times-circle text-red-600"></i>
                            </div>
                        </div>
                    </div>
                    
                    <div class="bg-white border border-gray-200 rounded-lg p-4">
                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-sm font-medium text-gray-500">待处理记录</div>
                                <div class="text-xl font-bold text-yellow-600">${pendingRecords}</div>
                            </div>
                            <div class="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center">
                                <i class="fas fa-clock text-yellow-600"></i>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        // 专门为数据页面加载记录的函数
        function loadDataPageRecords() {
            console.log('加载数据页面记录');
            
            // 获取分页参数
            const pageSizeEl = document.getElementById('page-size');
            const currentPageEl = document.getElementById('current-page');
            const limit = pageSizeEl ? parseInt(pageSizeEl.value) : 20;
            const page = currentPageEl ? parseInt(currentPageEl.textContent) : 1;
            
            fetch(`/api/v1/sync/records?limit=${limit}&page=${page}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('数据页面记录响应:', data);
                    
                    if (data.success) {
                        // 更新数据管理页面
                        updateDataRecordsTable(data.data.items || []);
                        updatePagination(data.data.pagination || {});
                    } else {
                        console.warn('数据页面记录加载失败:', data.message);
                        showNotification('记录加载失败: ' + (data.message || '未知错误'), 'error');
                    }
                })
                .catch(error => {
                    console.error('数据页面记录加载失败:', error);
                    showNotification('记录加载失败: ' + error.message, 'error');
                });
        }

        function loadMonitoringSyncRecords() {
            console.log('加载监控同步记录');
            
            // 检查当前页面类型，决定调用哪个更新函数
            const currentPageEl = document.querySelector('.page-content:not(.hidden)');
            const isDataPage = currentPageEl && currentPageEl.id === 'data-page';
            const isMonitoringPage = currentPageEl && currentPageEl.id === 'monitoring-page';
            
            // 获取分页参数
            let limit = isMonitoringPage ? 20 : 50;
            let page = 1;
            
            if (isDataPage) {
                const pageSizeEl = document.getElementById('page-size');
                const currentPageEl = document.getElementById('current-page');
                limit = pageSizeEl ? parseInt(pageSizeEl.value) : 20;
                page = currentPageEl ? parseInt(currentPageEl.textContent) : 1;
            }
            
            fetch(`/api/v1/sync/records?limit=${limit}&page=${page}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('监控同步记录响应:', data);
                    
                    if (data.success) {
                        if (isDataPage) {
                            // 数据管理页面
                            updateDataRecordsTable(data.data.items || []);
                            updatePagination(data.data.pagination || {});
                        } else if (isMonitoringPage) {
                            // 监控页面 - 更新表格和图表
                            updateMonitoringSyncTable(data.data);
                            updateSyncStatusChart(data.data);
                        }
                    } else {
                        console.warn('监控记录加载失败:', data.message);
                        if (isMonitoringPage) {
                            // 显示错误状态
                            const tableBody = document.getElementById('monitoring-sync-records');
                            if (tableBody) {
                                tableBody.innerHTML = '<tr><td colspan="6" class="px-6 py-8 text-center text-gray-500">加载失败: ' + (data.message || '未知错误') + '</td></tr>';
                            }
                        }
                    }
                })
                .catch(error => {
                    console.error('获取监控记录失败:', error);
                    if (isMonitoringPage) {
                        const tableBody = document.getElementById('monitoring-sync-records');
                        if (tableBody) {
                            tableBody.innerHTML = '<tr><td colspan="6" class="px-6 py-8 text-center text-gray-500">网络错误，请重试</td></tr>';
                        }
                    } else if (isDataPage) {
                        updateDataRecordsTable([]);
                    }
                });
        }

        function loadRealtimeData() {
            console.log('加载实时监控数据');
            fetch('/api/v1/monitoring/realtime?_=' + Date.now())
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('实时监控数据响应:', data);
                    if (data.success) {
                        updateRealtimeDisplay(data.data);
                    } else {
                        console.warn('实时数据加载失败:', data.message);
                    }
                })
                .catch(error => {
                    console.error('获取实时数据失败:', error);
                });
        }

        function loadMonitoringStats() {
            console.log('加载监控统计数据');
            fetch('/api/v1/monitoring/stats')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('监控统计数据响应:', data);
                    if (data.success) {
                        updateMonitoringStats(data.data);
                    } else {
                        console.warn('监控统计加载失败:', data.message);
                    }
                })
                .catch(error => {
                    console.error('获取监控统计失败:', error);
                });
        }

        function loadPerformanceData() {
            console.log('加载性能数据');
            fetch('/api/v1/monitoring/performance?_=' + Date.now())
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('性能数据响应:', data);
                    if (data.success) {
                        updatePerformanceChart(data.data);
                    } else {
                        console.warn('性能数据加载失败:', data.message);
                        // 如果API失败，使用模拟数据
                        updatePerformanceChart(null);
                    }
                })
                .catch(error => {
                    console.error('获取性能数据失败:', error);
                    // 网络错误时也使用模拟数据
                    updatePerformanceChart(null);
                });
        }

        // 更新函数
        function updateMonitoringSyncTable(records) {
            const tableBody = document.getElementById('monitoring-sync-records');
            if (!tableBody) {
                console.warn('监控页面同步记录表格未找到，表格ID应为: monitoring-sync-records');
                return;
            }
            
            if (!records || !records.items || records.items.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="6" class="px-6 py-8 text-center text-gray-500">暂无同步记录</td></tr>';
                return;
            }
            
            tableBody.innerHTML = records.items.slice(0, 10).map((record, index) => {
                const status = record.sync_status || 'pending';
                const statusClass = status === 'success' ? 'bg-green-100 text-green-800' : 
                                  status === 'failed' ? 'bg-red-100 text-red-800' : 
                                  status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 
                                  'bg-blue-100 text-blue-800';
                const statusText = status === 'success' ? '成功' : 
                                 status === 'failed' ? '失败' : 
                                 status === 'pending' ? '等待中' : '进行中';
                
                const documentName = record.document_title || record.title || 
                                   (record.source_id ? `文档 ${record.source_id.substring(0, 12)}...` : '未知文档');
                const displayId = record.source_id && record.source_id.length > 15 
                                ? record.source_id.substring(0, 15) + '...' 
                                : record.source_id || 'N/A';
                
                return `
                    <tr class="hover:bg-gray-50">
                        <td class="px-4 py-3 text-sm text-gray-900">${record.id || index + 1}</td>
                        <td class="px-4 py-3">
                            <div class="text-sm font-medium text-gray-900">${documentName}</div>
                            <div class="text-xs text-gray-500">${record.source_platform || '飞书'} → ${record.target_platform || 'Notion'}</div>
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-500" title="${record.source_id || ''}">${displayId}</td>
                        <td class="px-4 py-3">
                            <span class="inline-flex px-2 py-1 text-xs font-medium rounded-full ${statusClass}">
                                ${statusText}
                            </span>
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-500">${record.last_sync_time || record.updated_at || '未同步'}</td>
                        <td class="px-4 py-3 text-sm font-medium">
                            <button onclick="viewSyncDetails(${record.id})" class="text-blue-600 hover:text-blue-900 mr-2">查看</button>
                            ${status === 'failed' ? `<button onclick="retrySyncTask(${record.id})" class="text-green-600 hover:text-green-900">重试</button>` : ''}
                        </td>
                    </tr>
                `;
            }).join('');
        }
        
        function initMonitoringCharts() {
            console.log('初始化监控图表...');
            
            // 初始化同步状态分布图表
            const syncStatusCtx = document.getElementById('realtime-chart');
            if (syncStatusCtx && !window.syncStatusChart) {
                window.syncStatusChart = new Chart(syncStatusCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['成功', '失败', '待处理', '处理中'],
                        datasets: [{
                            data: [0, 0, 0, 0],
                            backgroundColor: [
                                '#10B981', // 成功 - 绿色
                                '#EF4444', // 失败 - 红色
                                '#F59E0B', // 待处理 - 黄色
                                '#3B82F6'  // 处理中 - 蓝色
                            ],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 10,
                                    usePointStyle: true
                                }
                            }
                        }
                    }
                });
            }
            
            // 初始化性能趋势图表
            const performanceCtx = document.getElementById('monitoring-performance-chart');
            if (performanceCtx && !window.performanceChart) {
                window.performanceChart = new Chart(performanceCtx, {
                    type: 'line',
                    data: {
                        labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
                        datasets: [{
                            label: '成功同步',
                            data: [0, 0, 0, 0, 0, 0, 0],
                            borderColor: '#10B981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            fill: true
                        }, {
                            label: '失败同步',
                            data: [0, 0, 0, 0, 0, 0, 0],
                            borderColor: '#EF4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        },
                        plugins: {
                            legend: {
                                position: 'bottom'
                            }
                        }
                    }
                });
            }
            
            console.log('监控图表初始化完成');
        }
        
        function initDashboardChart() {
            console.log('初始化仪表盘性能图表...');
            
            const dashboardCtx = document.getElementById('dashboard-performance-chart');
            if (dashboardCtx && !window.dashboardChart) {
                window.dashboardChart = new Chart(dashboardCtx, {
                    type: 'line',
                    data: {
                        labels: ['1周前', '6天前', '5天前', '4天前', '3天前', '2天前', '昨天', '今天'],
                        datasets: [{
                            label: '成功同步',
                            data: [0, 0, 0, 0, 0, 0, 0, 0],
                            borderColor: '#10B981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            fill: true,
                            tension: 0.4
                        }, {
                            label: '失败同步',
                            data: [0, 0, 0, 0, 0, 0, 0, 0],
                            borderColor: '#EF4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    stepSize: 1
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                position: 'top',
                                align: 'end'
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false
                            }
                        },
                        interaction: {
                            mode: 'nearest',
                            axis: 'x',
                            intersect: false
                        }
                    }
                });
                
                // 加载初始数据
                loadDashboardChartData();
            }
            
            console.log('仪表盘图表初始化完成');
        }
        
        function loadDashboardChartData() {
            console.log('加载仪表盘图表数据...');
            
            fetch('/api/v1/monitoring/performance?_=' + Date.now())
                .then(response => response.json())
                .then(data => {
                    if (data.success && window.dashboardChart) {
                        updateDashboardChart(data.data);
                    } else {
                        // 使用模拟数据
                        const mockData = {
                            daily_syncs: [
                                { sync_date: new Date(Date.now() - 7*24*60*60*1000).toISOString(), successful_syncs: 8, failed_syncs: 1 },
                                { sync_date: new Date(Date.now() - 6*24*60*60*1000).toISOString(), successful_syncs: 12, failed_syncs: 0 },
                                { sync_date: new Date(Date.now() - 5*24*60*60*1000).toISOString(), successful_syncs: 15, failed_syncs: 2 },
                                { sync_date: new Date(Date.now() - 4*24*60*60*1000).toISOString(), successful_syncs: 10, failed_syncs: 1 },
                                { sync_date: new Date(Date.now() - 3*24*60*60*1000).toISOString(), successful_syncs: 18, failed_syncs: 0 },
                                { sync_date: new Date(Date.now() - 2*24*60*60*1000).toISOString(), successful_syncs: 14, failed_syncs: 1 },
                                { sync_date: new Date(Date.now() - 1*24*60*60*1000).toISOString(), successful_syncs: 20, failed_syncs: 2 },
                                { sync_date: new Date().toISOString(), successful_syncs: 16, failed_syncs: 0 }
                            ]
                        };
                        updateDashboardChart(mockData);
                    }
                })
                .catch(error => {
                    console.error('获取仪表盘图表数据失败:', error);
                    // 使用默认模拟数据
                    const defaultData = {
                        daily_syncs: [
                            { sync_date: new Date(Date.now() - 7*24*60*60*1000).toISOString(), successful_syncs: 5, failed_syncs: 1 },
                            { sync_date: new Date(Date.now() - 6*24*60*60*1000).toISOString(), successful_syncs: 8, failed_syncs: 0 },
                            { sync_date: new Date(Date.now() - 5*24*60*60*1000).toISOString(), successful_syncs: 12, failed_syncs: 1 },
                            { sync_date: new Date(Date.now() - 4*24*60*60*1000).toISOString(), successful_syncs: 7, failed_syncs: 2 },
                            { sync_date: new Date(Date.now() - 3*24*60*60*1000).toISOString(), successful_syncs: 15, failed_syncs: 0 },
                            { sync_date: new Date(Date.now() - 2*24*60*60*1000).toISOString(), successful_syncs: 11, failed_syncs: 1 },
                            { sync_date: new Date(Date.now() - 1*24*60*60*1000).toISOString(), successful_syncs: 18, failed_syncs: 1 },
                            { sync_date: new Date().toISOString(), successful_syncs: 13, failed_syncs: 0 }
                        ]
                    };
                    updateDashboardChart(defaultData);
                });
        }
        
        function updateDashboardChart(performanceData) {
            console.log('更新仪表盘图表数据:', performanceData);
            
            if (!window.dashboardChart) {
                console.warn('仪表盘图表未初始化');
                return;
            }
            
            if (performanceData && performanceData.daily_syncs && Array.isArray(performanceData.daily_syncs)) {
                const dailyData = performanceData.daily_syncs;
                const labels = dailyData.map(item => {
                    const date = new Date(item.sync_date);
                    const today = new Date();
                    const diffTime = today - date;
                    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
                    
                    if (diffDays === 0) return '今天';
                    if (diffDays === 1) return '昨天';
                    return `${diffDays}天前`;
                });
                const successData = dailyData.map(item => item.successful_syncs || 0);
                const failedData = dailyData.map(item => item.failed_syncs || 0);
                
                window.dashboardChart.data.labels = labels;
                window.dashboardChart.data.datasets[0].data = successData;
                window.dashboardChart.data.datasets[1].data = failedData;
            }
            
            window.dashboardChart.update();
            console.log('仪表盘图表更新完成');
        }
        
        function updateSyncStatusChart(records) {
            console.log('更新同步状态分布图表:', records);
            if (!window.syncStatusChart) {
                console.warn('同步状态图表未初始化');
                return;
            }
            
            // 统计各种状态的数量
            const statusCounts = { success: 0, failed: 0, pending: 0, processing: 0 };
            
            if (records && records.items && Array.isArray(records.items)) {
                records.items.forEach(record => {
                    const status = record.sync_status || record.status || 'pending';
                    if (status === 'success' || status === 'completed') {
                        statusCounts.success++;
                    } else if (status === 'failed' || status === 'error') {
                        statusCounts.failed++;
                    } else if (status === 'pending') {
                        statusCounts.pending++;
                    } else {
                        statusCounts.processing++;
                    }
                });
            }
            
            // 更新图表数据
            window.syncStatusChart.data.datasets[0].data = [
                statusCounts.success, 
                statusCounts.failed, 
                statusCounts.pending, 
                statusCounts.processing
            ];
            
            window.syncStatusChart.update();
            console.log('同步状态分布图表更新完成:', statusCounts);
        }
        
        function updatePerformanceChart(performanceData) {
            console.log('更新性能趋势图表:', performanceData);
            if (!window.performanceChart) {
                console.warn('性能趋势图表未初始化');
                return;
            }
            
            // 如果有趋势数据，使用实际数据
            if (performanceData && performanceData.daily_syncs && Array.isArray(performanceData.daily_syncs)) {
                const dailyData = performanceData.daily_syncs;
                const labels = dailyData.map(item => {
                    const date = new Date(item.sync_date);
                    return `${date.getMonth() + 1}/${date.getDate()}`;
                });
                const successData = dailyData.map(item => item.successful_syncs || 0);
                const failedData = dailyData.map(item => item.failed_syncs || 0);
                
                window.performanceChart.data.labels = labels;
                window.performanceChart.data.datasets[0].data = successData;
                window.performanceChart.data.datasets[1].data = failedData;
            } else {
                // 使用模拟数据
                const mockData = {
                    success: [12, 19, 15, 25, 22, 18, 20],
                    failed: [2, 1, 3, 1, 2, 0, 1]
                };
                
                window.performanceChart.data.datasets[0].data = mockData.success;
                window.performanceChart.data.datasets[1].data = mockData.failed;
            }
            
            window.performanceChart.update();
            console.log('性能趋势图表更新完成');
        }
        
        function updateRealtimeDisplay(realtimeData) {
            console.log('更新实时监控显示:', realtimeData);
            
            // 更新活跃同步任务数 - 修正元素ID
            if (realtimeData.processing_tasks && Array.isArray(realtimeData.processing_tasks)) {
                const activeTasksElement = document.getElementById('active-syncs');
                if (activeTasksElement) {
                    activeTasksElement.textContent = realtimeData.processing_tasks.length;
                }
            }
            
            // 更新今日同步次数（从recent_activity中计算）
            if (realtimeData.recent_activity && Array.isArray(realtimeData.recent_activity)) {
                const todaySyncsElement = document.getElementById('today-syncs');
                if (todaySyncsElement) {
                    const totalSyncs = realtimeData.recent_activity.reduce((sum, activity) => sum + (activity.count || 0), 0);
                    todaySyncsElement.textContent = totalSyncs;
                }
            }
            
            // 更新平均响应时间 - 修正元素ID
            const avgResponseElement = document.getElementById('avg-response');
            if (avgResponseElement) {
                // 这里可以从realtimeData中获取实际的响应时间，暂时使用模拟数据
                const mockResponseTime = Math.floor(Math.random() * 500 + 100);
                avgResponseElement.textContent = `${mockResponseTime}ms`;
            }
            
            // 更新图片处理量 - 修正元素ID
            const imageProcessingElement = document.getElementById('image-processed');
            if (imageProcessingElement) {
                // 这里可以从realtimeData中获取实际的图片处理数据，暂时使用模拟数据
                const mockImageCount = Math.floor(Math.random() * 50) + 10;
                imageProcessingElement.textContent = mockImageCount;
            }
            
            console.log('实时监控显示更新完成');
        }

        function updateMonitoringStats(statsData) {
            console.log('更新监控统计数据:', statsData);
            
            // 更新总同步数
            if (statsData.total_stats && statsData.total_stats.total_syncs !== undefined) {
                const totalSyncsElement = document.getElementById('total-syncs');
                if (totalSyncsElement) {
                    totalSyncsElement.textContent = statsData.total_stats.total_syncs;
                }
            }
            
            // 更新成功率
            if (statsData.success_rate !== undefined) {
                const successRateElement = document.getElementById('success-rate');
                if (successRateElement) {
                    successRateElement.textContent = `${statsData.success_rate.toFixed(1)}%`;
                }
            }
            
            // 更新平均同步时间（模拟数据）
            const avgTimeElement = document.getElementById('avg-sync-time');
            if (avgTimeElement) {
                // 这里可以从statsData中获取实际的平均时间，暂时使用模拟数据
                const mockAvgTime = (Math.random() * 5 + 2).toFixed(1);
                avgTimeElement.textContent = `${mockAvgTime}s`;
            }
            
            console.log('监控统计数据更新完成');
        }

        // 重复的refreshDataView函数已移除，使用上面的版本

        function loadSystemStats() {
            console.log('加载系统统计');
            fetch('/api/v1/dashboard')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateSystemStatsDisplay(data.data);
                    } else {
                        showNotification('加载统计数据失败: ' + (data.message || 'Unknown error'), 'error');
                    }
                })
                .catch(error => {
                    console.error('获取系统统计失败:', error);
                    showNotification('加载统计数据失败: HTTP 404', 'error');
                });
        }

        function loadImageStats() {
            console.log('加载图片统计');
            fetch('/api/v1/images/stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateImageStatsDisplay(data.data);
                    } else {
                        console.warn('图片统计加载失败:', data.message);
                    }
                })
                .catch(error => {
                    console.error('获取图片统计失败:', error);
                });
        }

        function updateSystemStatsDisplay(data) {
            console.log('更新系统统计显示:', data);
            
            // 使用和数据统计页面相同的显示逻辑
            const statsContainer = document.getElementById('data-stats');
            if (!statsContainer) {
                console.warn('数据统计容器未找到');
                return;
            }
            
            // 调用统一的数据显示函数
            updateDataStatsDisplay(data);
        }

        function updateImageStatsDisplay(data) {
            console.log('更新图片统计显示:', data);
            // 这里可以实现具体的UI更新逻辑
        }

        function loadSystemSettings() {
            console.log('加载系统设置');
            
            // 加载系统信息
            loadSystemInfo();
            
            // 加载API配置信息（只显示部分信息，不显示敏感数据）
            loadApiConfigurations();
        }
        
        // 测试飞书API连接
        function testFeishuConnection() {
            const btn = document.getElementById('test-feishu-btn');
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>测试中...';
            btn.disabled = true;
            
            fetch('/api/v1/settings/test/feishu', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('飞书API连接测试成功', 'success');
                    btn.innerHTML = '<i class="fas fa-check mr-1"></i>连接成功';
                    btn.className = 'text-sm bg-green-600 text-white px-3 py-1 rounded-md hover:bg-green-700';
                } else {
                    showNotification('飞书API连接测试失败: ' + (data.message || '未知错误'), 'error');
                    btn.innerHTML = '<i class="fas fa-times mr-1"></i>连接失败';
                    btn.className = 'text-sm bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700';
                }
            })
            .catch(error => {
                console.error('飞书API测试连接失败:', error);
                showNotification('飞书API连接测试失败: 网络错误', 'error');
                btn.innerHTML = '<i class="fas fa-times mr-1"></i>连接失败';
                btn.className = 'text-sm bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700';
            })
            .finally(() => {
                btn.disabled = false;
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.className = 'text-sm bg-blue-600 text-white px-3 py-1 rounded-md hover:bg-blue-700';
                }, 3000);
            });
        }
        
        // 测试Notion API连接
        function testNotionConnection() {
            const btn = document.getElementById('test-notion-btn');
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>测试中...';
            btn.disabled = true;
            
            fetch('/api/v1/settings/test/notion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Notion API连接测试成功', 'success');
                    btn.innerHTML = '<i class="fas fa-check mr-1"></i>连接成功';
                    btn.className = 'text-sm bg-green-600 text-white px-3 py-1 rounded-md hover:bg-green-700';
                } else {
                    showNotification('Notion API连接测试失败: ' + (data.message || '未知错误'), 'error');
                    btn.innerHTML = '<i class="fas fa-times mr-1"></i>连接失败';
                    btn.className = 'text-sm bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700';
                }
            })
            .catch(error => {
                console.error('Notion API测试连接失败:', error);
                showNotification('Notion API连接测试失败: 网络错误', 'error');
                btn.innerHTML = '<i class="fas fa-times mr-1"></i>连接失败';
                btn.className = 'text-sm bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700';
            })
            .finally(() => {
                btn.disabled = false;
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.className = 'text-sm bg-gray-600 text-white px-3 py-1 rounded-md hover:bg-gray-700';
                }, 3000);
            });
        }
        
        // 测试七牛云存储连接
        function testQiniuConnection() {
            const btn = document.getElementById('test-qiniu-btn');
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>测试中...';
            btn.disabled = true;
            
            fetch('/api/v1/settings/test/qiniu', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('七牛云存储连接测试成功', 'success');
                    btn.innerHTML = '<i class="fas fa-check mr-1"></i>连接成功';
                    btn.className = 'text-sm bg-green-600 text-white px-3 py-1 rounded-md hover:bg-green-700';
                } else {
                    showNotification('七牛云存储连接测试失败: ' + (data.message || '未知错误'), 'error');
                    btn.innerHTML = '<i class="fas fa-times mr-1"></i>连接失败';
                    btn.className = 'text-sm bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700';
                }
            })
            .catch(error => {
                console.error('七牛云存储测试连接失败:', error);
                showNotification('七牛云存储连接测试失败: 网络错误', 'error');
                btn.innerHTML = '<i class="fas fa-times mr-1"></i>连接失败';
                btn.className = 'text-sm bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700';
            })
            .finally(() => {
                btn.disabled = false;
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.className = 'text-sm bg-green-600 text-white px-3 py-1 rounded-md hover:bg-green-700';
                }, 3000);
            });
        }
        
        // 加载系统信息
        function loadSystemInfo() {
            fetch('/api/v1/settings/system/info')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateSystemInfo(data.data);
                    } else {
                        console.warn('获取系统信息失败:', data.message);
                    }
                })
                .catch(error => {
                    console.error('获取系统信息失败:', error);
                });
        }
        
        // 更新系统信息显示
        function updateSystemInfo(info) {
            // 更新系统运行时间
            const uptimeElement = document.getElementById('system-uptime');
            if (uptimeElement && info.uptime) {
                uptimeElement.textContent = info.uptime;
            }
            
            // 更新存储使用量
            const storageElement = document.getElementById('storage-usage');
            if (storageElement && info.storage_usage) {
                storageElement.textContent = info.storage_usage;
            }
            
            // 更新API连接状态
            const apiStatusElement = document.getElementById('api-status-count');
            if (apiStatusElement && info.api_status) {
                apiStatusElement.textContent = info.api_status;
            }
            
            // 更新系统版本
            const versionElement = document.getElementById('system-version');
            if (versionElement && info.version) {
                versionElement.textContent = info.version;
            }
        }
        
        // 加载API配置信息
        function loadApiConfigurations() {
            fetch('/api/v1/settings/api/configs')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateApiConfigurations(data.data);
                    } else {
                        console.warn('获取API配置失败:', data.message);
                    }
                })
                .catch(error => {
                    console.error('获取API配置失败:', error);
                });
        }
        
        // 更新API配置显示
        function updateApiConfigurations(configs) {
            // 更新飞书配置
            if (configs.feishu) {
                const appIdElement = document.getElementById('feishu-app-id');
                if (appIdElement && configs.feishu.app_id) {
                    appIdElement.value = configs.feishu.app_id;
                }
            }
            
            // 更新Notion配置
            if (configs.notion) {
                const databaseIdElement = document.getElementById('notion-database-id');
                if (databaseIdElement && configs.notion.database_id) {
                    databaseIdElement.value = configs.notion.database_id;
                }
            }
            
            // 更新七牛云配置
            if (configs.qiniu) {
                const accessKeyElement = document.getElementById('qiniu-access-key');
                const bucketElement = document.getElementById('qiniu-bucket');
                const cdnDomainElement = document.getElementById('qiniu-cdn-domain');
                
                if (accessKeyElement && configs.qiniu.access_key) {
                    accessKeyElement.value = configs.qiniu.access_key;
                }
                if (bucketElement && configs.qiniu.bucket) {
                    bucketElement.value = configs.qiniu.bucket;
                }
                if (cdnDomainElement && configs.qiniu.cdn_domain) {
                    cdnDomainElement.value = configs.qiniu.cdn_domain;
                }
            }
        }
        
        // 保存同步参数设置
        function saveSyncSettings() {
            const btn = document.getElementById('save-sync-settings-btn');
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>保存中...';
            btn.disabled = true;
            
            // 收集表单数据
            const settings = {
                sync_timeout: document.getElementById('sync-timeout')?.value || 60,
                retry_count: document.getElementById('retry-count')?.value || 3,
                batch_size: document.getElementById('batch-size')?.value || 10,
                auto_retry: document.getElementById('auto-retry')?.checked || false,
                image_quality: document.getElementById('image-quality')?.value || 70,
                log_retention: document.getElementById('log-retention')?.value || 30,
                enable_webhook: document.getElementById('enable-webhook')?.checked || true
            };
            
            fetch('/api/v1/settings/sync/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('同步参数设置保存成功', 'success');
                    btn.innerHTML = '<i class="fas fa-check mr-1"></i>保存成功';
                    btn.className = 'text-sm bg-green-600 text-white px-3 py-1 rounded-md hover:bg-green-700';
                } else {
                    showNotification('保存设置失败: ' + (data.message || '未知错误'), 'error');
                    btn.innerHTML = '<i class="fas fa-times mr-1"></i>保存失败';
                    btn.className = 'text-sm bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700';
                }
            })
            .catch(error => {
                console.error('保存同步设置失败:', error);
                showNotification('保存设置失败: 网络错误', 'error');
                btn.innerHTML = '<i class="fas fa-times mr-1"></i>保存失败';
                btn.className = 'text-sm bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700';
            })
            .finally(() => {
                btn.disabled = false;
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.className = 'text-sm bg-orange-600 text-white px-3 py-1 rounded-md hover:bg-orange-700';
                }, 3000);
            });
        }

        function initHelpPage() {
            console.log('初始化帮助页面');
            // 帮助页面的初始化逻辑
        }

        // 数据管理页面：切换数据视图
        function switchDataView() {
            const viewType = document.getElementById('data-view-type').value;
            const syncRecordsView = document.getElementById('sync-records-view');
            const imagesView = document.getElementById('images-view');
            const actionArea = document.getElementById('data-action-area');
            
            console.log('切换数据视图:', viewType);
            
            if (viewType === 'images') {
                // 显示图片管理
                syncRecordsView.classList.add('hidden');
                imagesView.classList.remove('hidden');
                actionArea.classList.add('hidden'); // 隐藏同步记录的操作按钮
                
                // 加载图片数据
                loadImageStats();
                loadImagesList();
            } else {
                // 显示同步记录
                syncRecordsView.classList.remove('hidden');
                imagesView.classList.add('hidden');
                actionArea.classList.remove('hidden'); // 显示同步记录的操作按钮
                
                // 加载同步记录数据
                loadMonitoringSyncRecords();
            }
        }


        // 更新图片统计显示
        function updateImageStatsDisplay(stats) {
            if (!stats) return;
            
            const totalImagesEl = document.getElementById('total-images');
            if (totalImagesEl) totalImagesEl.textContent = stats.total_images || 0;
            
            const storageUsedEl = document.getElementById('storage-used');
            if (storageUsedEl) storageUsedEl.textContent = formatFileSize(stats.total_size || 0);
            
            const todayProcessedEl = document.getElementById('today-processed');
            if (todayProcessedEl) todayProcessedEl.textContent = stats.today_processed || 0;
        }

        // 加载图片列表
        function loadImagesList() {
            console.log('加载图片列表');
            
            const tableBody = document.getElementById('images-table-body');
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-8 text-center text-gray-500">
                        <div class="loading-spinner inline-block mr-2"></div>
                        <span>加载图片数据...</span>
                    </td>
                </tr>
            `;
            
            fetch('/api/v1/images/list')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateImagesTable(data.data);
                    } else {
                        tableBody.innerHTML = `
                            <tr>
                                <td colspan="7" class="px-6 py-8 text-center text-gray-500">
                                    <i class="fas fa-exclamation-triangle text-red-500 mr-2"></i>
                                    <span>加载图片列表失败: ${data.message || 'Unknown error'}</span>
                                </td>
                            </tr>
                        `;
                    }
                })
                .catch(error => {
                    console.error('获取图片列表失败:', error);
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="7" class="px-6 py-8 text-center text-gray-500">
                                <i class="fas fa-wifi-slash text-red-500 mr-2"></i>
                                <span>网络错误，请检查连接并重试</span>
                            </td>
                        </tr>
                    `;
                });
        }

        // 更新图片表格
        function updateImagesTable(images) {
            const tableBody = document.getElementById('images-table-body');
            
            if (!Array.isArray(images) || images.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="7" class="px-6 py-8 text-center text-gray-500">
                            <i class="fas fa-images text-gray-300 text-2xl mb-2"></i>
                            <div>暂无图片数据</div>
                        </td>
                    </tr>
                `;
                return;
            }
            
            const imagesHTML = images.map(image => `
                <tr class="hover:bg-gray-50">
                    <td class="px-4 py-3">
                        <img src="${image.qiniu_url}" alt="预览" class="w-16 h-16 object-cover rounded-lg border border-gray-200" 
                             onerror="this.src='data:image/svg+xml,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"64\" height=\"64\" fill=\"%23ccc\"><rect width=\"64\" height=\"64\" fill=\"%23f5f5f5\"/><text x=\"50%\" y=\"50%\" text-anchor=\"middle\" dy=\".3em\" fill=\"%23999\">?</text></svg>'" />
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-500 max-w-xs truncate" title="${image.original_url}">
                        ${image.original_url}
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-500 max-w-xs">
                        <a href="${image.qiniu_url}" target="_blank" class="text-blue-600 hover:text-blue-800 truncate block" title="${image.qiniu_url}">
                            ${image.qiniu_url.split('/').pop()}
                        </a>
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-900">
                        ${formatFileSize(image.file_size)}
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-500">
                        ${getTimeAgo(image.upload_time)}
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-900">
                        ${image.access_count || 0}
                    </td>
                    <td class="px-4 py-3 text-sm font-medium">
                        <button onclick="copyToClipboard('${image.qiniu_url}')" class="text-blue-600 hover:text-blue-900 mr-2">复制链接</button>
                        <button onclick="deleteImage('${image.id}')" class="text-red-600 hover:text-red-900">删除</button>
                    </td>
                </tr>
            `).join('');
            
            tableBody.innerHTML = imagesHTML;
        }

        // 格式化文件大小
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        // 复制到剪贴板
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                showNotification('链接已复制到剪贴板', 'success');
            }).catch(err => {
                console.error('复制失败:', err);
                showNotification('复制失败，请手动复制', 'error');
            });
        }

        // 删除图片
        function deleteImage(imageId) {
            if (!confirm('确定要删除这张图片吗？此操作不可撤销。')) {
                return;
            }
            
            fetch(`/api/v1/images/${imageId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('图片删除成功', 'success');
                    loadImagesList(); // 重新加载列表
                    loadImageStats(); // 重新加载统计
                } else {
                    showNotification(data.message || '删除失败', 'error');
                }
            })
            .catch(error => {
                console.error('删除图片失败:', error);
                showNotification('删除失败: ' + error.message, 'error');
            });
        }

        // 分页相关函数
        function updatePagination(pagination) {
            console.log('更新分页信息:', pagination);
            
            const totalRecords = document.getElementById('total-records');
            const currentPage = document.getElementById('current-page');
            const totalPages = document.getElementById('total-pages');
            const pageNumbers = document.getElementById('page-numbers');
            
            if (!totalRecords || !currentPage || !totalPages) {
                console.warn('分页元素未找到');
                return;
            }
            
            // 更新数字显示
            totalRecords.textContent = pagination.total || 0;
            currentPage.textContent = pagination.page || 1;
            totalPages.textContent = pagination.pages || 1;
            
            // 更新按钮状态
            updatePaginationButtons(pagination.page || 1, pagination.pages || 1);
            
            // 生成页码按钮
            if (pageNumbers) {
                generatePageNumbers(pagination.page || 1, pagination.pages || 1);
            }
        }
        
        function changePage(page) {
            console.log('切换到第', page, '页');
            const currentPageEl = document.getElementById('current-page');
            if (currentPageEl) {
                currentPageEl.textContent = page;
            }
            
            // 更新上一页下一页按钮状态
            const totalPagesEl = document.getElementById('total-pages');
            const totalPages = totalPagesEl ? parseInt(totalPagesEl.textContent) : 1;
            updatePaginationButtons(page, totalPages);
            
            // 直接调用数据页面记录加载函数
            loadDataPageRecords();
        }
        
        
        function generatePageNumbers(currentPage, totalPages) {
            const pageNumbers = document.getElementById('page-numbers');
            if (!pageNumbers) return;
            
            pageNumbers.innerHTML = '';
            
            // 计算显示范围
            let startPage = Math.max(1, currentPage - 2);
            let endPage = Math.min(totalPages, currentPage + 2);
            
            // 如果总页数少于等于5页，显示所有页码
            if (totalPages <= 5) {
                startPage = 1;
                endPage = totalPages;
            }
            
            // 添加第一页
            if (startPage > 1) {
                addPageButton(pageNumbers, 1, currentPage);
                if (startPage > 2) {
                    addEllipsis(pageNumbers);
                }
            }
            
            // 添加中间页码
            for (let i = startPage; i <= endPage; i++) {
                addPageButton(pageNumbers, i, currentPage);
            }
            
            // 添加最后一页
            if (endPage < totalPages) {
                if (endPage < totalPages - 1) {
                    addEllipsis(pageNumbers);
                }
                addPageButton(pageNumbers, totalPages, currentPage);
            }
        }
        
        function addPageButton(container, pageNum, currentPage) {
            const button = document.createElement('button');
            button.textContent = pageNum;
            button.className = `px-3 py-2 text-sm rounded-md ${
                pageNum === currentPage 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`;
            // 使用addEventListener而不是onclick，添加调试
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('页码按钮被点击:', pageNum);
                changePage(pageNum);
            });
            container.appendChild(button);
        }
        
        function addEllipsis(container) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'px-3 py-2 text-sm text-gray-500';
            container.appendChild(ellipsis);
        }
        
        function updatePaginationButtons(currentPage, totalPages) {
            const prevPageBtn = document.getElementById('prev-page');
            const nextPageBtn = document.getElementById('next-page');
            
            if (prevPageBtn) {
                prevPageBtn.disabled = currentPage <= 1;
                prevPageBtn.classList.toggle('opacity-50', currentPage <= 1);
                prevPageBtn.classList.toggle('cursor-not-allowed', currentPage <= 1);
            }
            
            if (nextPageBtn) {
                nextPageBtn.disabled = currentPage >= totalPages;
                nextPageBtn.classList.toggle('opacity-50', currentPage >= totalPages);
                nextPageBtn.classList.toggle('cursor-not-allowed', currentPage >= totalPages);
            }
        }

        function changePageSize() {
            console.log('修改页面大小');
            // 重置到第一页
            const currentPageEl = document.getElementById('current-page');
            if (currentPageEl) {
                currentPageEl.textContent = '1';
            }
            
            // 重置分页按钮状态
            updatePaginationButtons(1, 1);
            
            // 直接调用数据页面记录加载函数
            loadDataPageRecords();
        }

        // 添加缺失的同步任务重试函数
        function retrySyncTask(recordId) {
            if (!recordId) {
                showNotification('记录ID无效', 'error');
                return;
            }
            
            if (!confirm('确定要重试这个同步任务吗？')) {
                return;
            }
            
            console.log('重试同步任务:', recordId);
            
            fetch(`/api/v1/sync/records/${recordId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'retry'
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showNotification('重试任务已提交', 'success');
                    // 刷新数据，根据当前页面决定调用哪个函数
                    setTimeout(() => {
                        const currentPageEl = document.querySelector('.page-content:not(.hidden)');
                        if (currentPageEl && currentPageEl.id === 'data-page') {
                            refreshDataView();
                        } else {
                            loadMonitoringSyncRecords();
                        }
                    }, 1000);
                } else {
                    showNotification(data.message || '重试失败', 'error');
                }
            })
            .catch(error => {
                console.error('重试同步任务失败:', error);
                showNotification('重试请求失败: ' + error.message, 'error');
            });
        }

        // 新增：更新数据管理页面的记录表格
        function updateDataRecordsTable(records) {
            const tableBody = document.getElementById('data-records-body');
            if (!tableBody) {
                console.warn('数据记录表格容器未找到');
                return;
            }
            
            // 确保records是数组
            if (!Array.isArray(records)) {
                records = [];
            }
            
            if (records.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                            <i class="fas fa-database mr-2"></i>
                            <span>暂无同步记录</span>
                            <button onclick="refreshDataView()" class="ml-4 px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600">
                                刷新
                            </button>
                        </td>
                    </tr>
                `;
                return;
            }
            
            // 生成表格行HTML
            const rowsHTML = records.map((record, index) => {
                // 统一状态处理
                const status = record.sync_status || record.status || 'pending';
                const statusClass = status === 'success' || status === 'completed' ? 'bg-green-100 text-green-800' : 
                                  status === 'failed' || status === 'error' ? 'bg-red-100 text-red-800' : 
                                  status === 'processing' ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800';
                const statusIcon = status === 'success' || status === 'completed' ? 'fa-check-circle' : 
                                 status === 'failed' || status === 'error' ? 'fa-times-circle' : 
                                 status === 'processing' ? 'fa-spinner fa-spin' : 'fa-clock';
                
                // 状态文本
                const statusText = status === 'success' || status === 'completed' ? '同步成功' : 
                                 status === 'failed' || status === 'error' ? '同步失败' : 
                                 status === 'processing' ? '同步中' : '等待同步';
                
                // 文档标题处理
                const documentTitle = record.document_title || record.title || 
                                    (record.source_id ? `文档 ${record.source_id.substring(0, 8)}...` : '未知文档');
                
                // 记录编号显示（阿拉伯数字，从1开始）
                const recordNumber = index + 1;
                
                // 文档ID显示（截断显示）
                const documentId = record.source_id || record.document_id || 'N/A';
                const displayId = documentId.length > 20 ? documentId.substring(0, 20) + '...' : documentId;
                
                // 时间格式化
                const syncTime = record.last_sync_time || record.created_at || record.updated_at;
                const displayTime = syncTime ? formatFullTime(syncTime) : '未知时间';
                
                // 错误信息处理
                const errorMessage = record.error_message || '';
                const hasError = status === 'failed' || status === 'error';
                
                return `
                    <tr class="table-row hover:bg-gray-50" data-record-id="${record.id}">
                        <td class="px-4 py-3 text-sm text-gray-900">${recordNumber}</td>
                        <td class="px-4 py-3">
                            <div class="text-sm font-medium text-gray-900" title="${documentTitle}">
                                ${documentTitle.length > 30 ? documentTitle.substring(0, 30) + '...' : documentTitle}
                            </div>
                            ${record.source_platform ? `<div class="text-xs text-gray-500">来源: ${record.source_platform}</div>` : ''}
                        </td>
                        <td class="px-4 py-3">
                            <div class="text-sm text-gray-900 font-mono" title="${documentId}">
                                ${displayId}
                            </div>
                        </td>
                        <td class="px-4 py-3">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusClass}">
                                <i class="fas ${statusIcon} mr-1"></i>
                                ${statusText}
                            </span>
                            ${hasError && errorMessage ? `<div class="text-xs text-red-600 mt-1" title="${errorMessage}">错误: ${errorMessage.substring(0, 50)}${errorMessage.length > 50 ? '...' : ''}</div>` : ''}
                        </td>
                        <td class="px-4 py-3 text-sm text-gray-500">
                            ${displayTime}
                        </td>
                        <td class="px-4 py-3 text-sm font-medium">
                            <div class="flex items-center space-x-2">
                                ${hasError ? `<button onclick="retrySyncTask(${record.id})" class="text-blue-600 hover:text-blue-900" title="重试同步">
                                    <i class="fas fa-redo-alt"></i>
                                </button>` : ''}
                                <button onclick="viewSyncDetail(${record.id})" class="text-green-600 hover:text-green-900" title="查看详情">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button onclick="deleteSyncRecord(${record.id})" class="text-red-600 hover:text-red-900" title="删除记录">
                                    <i class="fas fa-trash-alt"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
            
            tableBody.innerHTML = rowsHTML;
            console.log(`数据记录表格更新完成，显示 ${records.length} 条记录`);
        }

        // 查看同步记录详情
        function viewSyncDetail(recordId) {
            console.log('查看同步记录详情:', recordId);
            
            fetch(`/api/v1/sync/records/${recordId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        showSyncDetailModal(data.data);
                    } else {
                        showNotification('获取记录详情失败: ' + (data.message || '未知错误'), 'error');
                    }
                })
                .catch(error => {
                    console.error('获取记录详情失败:', error);
                    showNotification('获取记录详情失败: ' + error.message, 'error');
                });
        }

        // 显示同步详情模态框
        function showSyncDetailModal(record) {
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
            modal.id = 'sync-detail-modal';
            
            const status = record.sync_status || record.status || 'pending';
            const statusClass = status === 'success' || status === 'completed' ? 'text-green-600' : 
                              status === 'failed' || status === 'error' ? 'text-red-600' : 
                              status === 'processing' ? 'text-blue-600' : 'text-yellow-600';
            
            modal.innerHTML = `
                <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
                    <div class="mt-3">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-lg font-medium text-gray-900">同步记录详情</h3>
                            <button onclick="closeSyncDetailModal()" class="text-gray-400 hover:text-gray-600">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        
                        <div class="space-y-4">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">记录编号</label>
                                    <div class="mt-1 text-sm text-gray-900">${record.record_number || record.id}</div>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">同步状态</label>
                                    <div class="mt-1">
                                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusClass.replace('text-', 'bg-').replace('-600', '-100')} ${statusClass}">
                                            ${status === 'success' || status === 'completed' ? '同步成功' : 
                                              status === 'failed' || status === 'error' ? '同步失败' : 
                                              status === 'processing' ? '同步中' : '等待同步'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            
                            <div>
                                <label class="block text-sm font-medium text-gray-700">文档标题</label>
                                <div class="mt-1 text-sm text-gray-900">${record.document_title || record.title || '未知文档'}</div>
                            </div>
                            
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">源平台</label>
                                    <div class="mt-1 text-sm text-gray-900">${record.source_platform || 'N/A'}</div>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">目标平台</label>
                                    <div class="mt-1 text-sm text-gray-900">${record.target_platform || 'N/A'}</div>
                                </div>
                            </div>
                            
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">源文档ID</label>
                                    <div class="mt-1 text-sm text-gray-900 font-mono break-all">${record.source_id || 'N/A'}</div>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">目标文档ID</label>
                                    <div class="mt-1 text-sm text-gray-900 font-mono break-all">${record.target_id || 'N/A'}</div>
                                </div>
                            </div>
                            
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">创建时间</label>
                                    <div class="mt-1 text-sm text-gray-900">${record.created_at ? formatFullTime(record.created_at) : 'N/A'}</div>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">最后同步时间</label>
                                    <div class="mt-1 text-sm text-gray-900">${record.last_sync_time ? formatFullTime(record.last_sync_time) : 'N/A'}</div>
                                </div>
                            </div>
                            
                            ${record.error_message ? `
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">错误信息</label>
                                    <div class="mt-1 p-3 bg-red-50 border border-red-200 rounded-md">
                                        <div class="text-sm text-red-800">${record.error_message}</div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                        
                        <div class="mt-6 flex justify-end space-x-3">
                            ${(status === 'failed' || status === 'error') ? `
                                <button onclick="retrySyncTask(${record.id}); closeSyncDetailModal();" 
                                        class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700">
                                    重试同步
                                </button>
                            ` : ''}
                            <button onclick="closeSyncDetailModal()" 
                                    class="px-4 py-2 bg-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-400">
                                关闭
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
        }

        // 关闭同步详情模态框
        function closeSyncDetailModal() {
            const modal = document.getElementById('sync-detail-modal');
            if (modal) {
                modal.remove();
            }
        }

        // 删除同步记录
        function deleteSyncRecord(recordId) {
            if (!confirm('确定要删除这条同步记录吗？此操作不可撤销。')) {
                return;
            }
            
            console.log('删除同步记录:', recordId);
            
            fetch(`/api/v1/sync/records/${recordId}`, {
                method: 'DELETE'
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        showNotification('同步记录删除成功', 'success');
                        // 刷新数据视图
                        refreshDataView();
                    } else {
                        showNotification('删除记录失败: ' + (data.message || '未知错误'), 'error');
                    }
                })
                .catch(error => {
                    console.error('删除记录失败:', error);
                    showNotification('删除记录失败: ' + error.message, 'error');
                });
        }


        function showVersionInfo() {
            console.log('显示版本信息');
            showNotification('版本信息功能开发中', 'info');
        }

        // 页面初始化
        document.addEventListener('DOMContentLoaded', function() {
            console.log('页面初始化完成');
            
            // 初始化数据管理页面分页控制（包含页面大小选择器绑定）
            initDataPagePagination();
        });
        
        function initDataPagePagination() {
            console.log('初始化数据页面分页控制');
            
            // 绑定页面大小选择器事件（使用一次性绑定）
            const pageSizeSelect = document.getElementById('page-size');
            if (pageSizeSelect && !pageSizeSelect.hasAttribute('data-listener-bound')) {
                pageSizeSelect.addEventListener('change', (e) => {
                    console.log('页面大小选择器被点击，新值:', e.target.value);
                    changePageSize();
                });
                pageSizeSelect.setAttribute('data-listener-bound', 'true');
                console.log('页面大小选择器事件已绑定');
            }
            
            // 绑定批量重试按钮事件（使用一次性绑定）
            const retryButtons = document.querySelectorAll('#data-retry-buttons button');
            retryButtons.forEach((btn, index) => {
                if (!btn.hasAttribute('data-listener-bound')) {
                    const statuses = ['pending', 'failed', 'all'];
                    const status = statuses[index] || 'all';
                    btn.addEventListener('click', () => batchRetryRecords(status));
                    btn.setAttribute('data-listener-bound', 'true');
                    console.log(`绑定批量重试按钮: ${status}`);
                }
            });
            
            // 绑定批量删除按钮事件（使用一次性绑定）
            const deleteButtons = document.querySelectorAll('#data-delete-buttons button');
            deleteButtons.forEach((btn, index) => {
                if (!btn.hasAttribute('data-listener-bound')) {
                    const statuses = ['failed', 'processing', 'all'];
                    const status = statuses[index] || 'all';
                    btn.addEventListener('click', () => batchDeleteRecords(status));
                    btn.setAttribute('data-listener-bound', 'true');
                    console.log(`绑定批量删除按钮: ${status}`);
                }
            });
            
            // 绑定页面导航按钮事件（使用一次性绑定）
            const prevPageBtn = document.getElementById('prev-page');
            const nextPageBtn = document.getElementById('next-page');
            
            if (prevPageBtn && !prevPageBtn.hasAttribute('data-listener-bound')) {
                prevPageBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('上一页按钮被点击');
                    const currentPageEl = document.getElementById('current-page');
                    const currentPage = currentPageEl ? parseInt(currentPageEl.textContent) : 1;
                    if (currentPage > 1 && !prevPageBtn.disabled) {
                        console.log('执行上一页操作:', currentPage - 1);
                        changePage(currentPage - 1);
                    } else {
                        console.log('上一页按钮被禁用或已在第一页');
                    }
                });
                prevPageBtn.setAttribute('data-listener-bound', 'true');
                console.log('上一页按钮事件已绑定');
            }
            
            if (nextPageBtn && !nextPageBtn.hasAttribute('data-listener-bound')) {
                nextPageBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('下一页按钮被点击');
                    const currentPageEl = document.getElementById('current-page');
                    const totalPagesEl = document.getElementById('total-pages');
                    const currentPage = currentPageEl ? parseInt(currentPageEl.textContent) : 1;
                    const totalPages = totalPagesEl ? parseInt(totalPagesEl.textContent) : 1;
                    if (currentPage < totalPages && !nextPageBtn.disabled) {
                        console.log('执行下一页操作:', currentPage + 1);
                        changePage(currentPage + 1);
                    } else {
                        console.log('下一页按钮被禁用或已在最后一页');
                    }
                });
                nextPageBtn.setAttribute('data-listener-bound', 'true');
                console.log('下一页按钮事件已绑定');
            }
            
            console.log('数据页面分页控制初始化完成');
        }
        
        // 批量重试记录函数
        function batchRetryRecords(status) {
            console.log(`批量重试记录: ${status}`);
            
            let confirmMessage = '';
            let apiUrl = '';
            let requestData = {};
            
            if (status === 'pending') {
                confirmMessage = '确定要重试所有待处理任务吗？';
                // 获取待处理任务的记录ID
                requestData = { status: 'pending' };
            } else if (status === 'failed') {
                confirmMessage = '确定要重试所有失败任务吗？';
                requestData = { status: 'failed' };
            } else if (status === 'all') {
                confirmMessage = '确定要重试所有未完成任务吗？这将包括待处理和失败的任务。';
                requestData = { status: 'all' };
            }
            
            if (!confirm(confirmMessage)) {
                return;
            }
            
            // 显示加载状态
            showNotification('正在执行批量重试操作...', 'info');
            
            // 先获取要重试的记录ID
            fetch('/api/v1/sync/records?status=' + (status === 'all' ? 'failed' : status) + '&limit=100')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.data.items) {
                        const recordIds = data.data.items.map(item => item.id);
                        
                        if (recordIds.length === 0) {
                            showNotification('没有找到需要重试的记录', 'warning');
                            return;
                        }
                        
                        // 执行批量重试
                        return fetch('/api/v1/sync/records/batch', {
                            method: 'PATCH',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                record_ids: recordIds,
                                retry_failed_only: status !== 'all'
                            })
                        });
                    } else {
                        throw new Error('获取记录列表失败');
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification(`批量重试成功：${data.data.updated_count} 条记录已重新提交`, 'success');
                        // 刷新数据视图
                        refreshDataView();
                    } else {
                        showNotification('批量重试失败：' + (data.message || '未知错误'), 'error');
                    }
                })
                .catch(error => {
                    console.error('批量重试失败:', error);
                    showNotification('批量重试失败：网络错误', 'error');
                });
        }
        
        // 批量删除记录函数
        function batchDeleteRecords(status) {
            console.log(`批量删除记录: ${status}`);
            
            let confirmMessage = '';
            let dangerLevel = '';
            
            if (status === 'failed') {
                confirmMessage = '确定要删除所有失败记录吗？此操作不可撤销！';
                dangerLevel = 'warning';
            } else if (status === 'processing') {
                confirmMessage = '确定要删除所有进行中记录吗？此操作不可撤销！';
                dangerLevel = 'warning';
            } else if (status === 'all') {
                confirmMessage = '⚠️ 危险操作：确定要删除所有记录吗？\n\n此操作将永久删除所有同步记录，无法恢复！\n\n请输入 "DELETE" 确认操作:';
                dangerLevel = 'danger';
            }
            
            if (dangerLevel === 'danger') {
                const userConfirm = prompt(confirmMessage);
                if (userConfirm !== 'DELETE') {
                    showNotification('操作已取消', 'info');
                    return;
                }
            } else {
                if (!confirm(confirmMessage)) {
                    return;
                }
            }
            
            // 显示加载状态
            showNotification('正在执行批量删除操作...', 'info');
            
            let requestData = {};
            
            if (status === 'all') {
                // 删除所有记录
                requestData = { status: 'all' };
            } else {
                // 删除特定状态的记录
                requestData = { status: status };
            }
            
            fetch('/api/v1/sync/records/batch', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(`批量删除成功：${data.data.deleted_count} 条记录已删除`, 'success');
                    // 刷新数据视图
                    refreshDataView();
                } else {
                    showNotification('批量删除失败：' + (data.message || '未知错误'), 'error');
                }
            })
            .catch(error => {
                console.error('批量删除失败:', error);
                showNotification('批量删除失败：网络错误', 'error');
            });
        }
