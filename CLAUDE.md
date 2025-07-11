# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Feishu-Notion bidirectional synchronization system that enables automatic content syncing between Feishu (Lark) documents and Notion pages. The system includes image processing via Qiniu Cloud CDN, format conversion, and a web management interface.

## Commands

### Running the Application
```bash
# Start the Flask development server (uses application factory pattern)
python app.py

# Start in production mode with logging
nohup python app.py > server.log 2>&1 &

# Check if service is running
ps aux | grep "python app.py"

# Kill the service
pkill -f "python app.py"

# Check application health
curl http://localhost:5000/health
curl https://sync.yianlu.com/health
```

### Database Management
```bash
# Initialize database (first time setup)
python database/init_db.py

# Run database migration from old SQLite to SQLAlchemy
python database/migration_service.py

# Initialize Alembic migrations
alembic init alembic

# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1

# View migration history
alembic history --verbose

# Check current migration status
alembic current

# Show SQL for migration (dry run)
alembic upgrade head --sql
```

### Health Checks and Monitoring
```bash
# Check service health
curl http://localhost:5000/health
curl https://sync.yianlu.com/health

# View application logs
tail -f app.log
tail -f server.log

# Monitor sync task processor logs
tail -f logs/sync_processor.log
```

### Development and Testing
Since this project doesn't have formal test infrastructure, testing is done manually:

```bash
# Install dependencies
pip install -r requirements.txt

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
venv\Scripts\activate     # On Windows

# Check for syntax errors
python -m py_compile app.py
find app -name "*.py" -exec python -m py_compile {} \;

# Validate configuration and service connections
python -c "
from config.settings import settings
print('Feishu configured:', settings.is_feishu_configured())
print('Notion configured:', settings.is_notion_configured()) 
print('Qiniu configured:', settings.is_qiniu_configured())
"

# Test database connection
python -c "
from database.connection import db
print('Database connection test:', db.test_connection())
"

# Run a specific sync manually (via Python console)
python -c "
from app.services.sync_processor import SyncProcessor
processor = SyncProcessor()
processor.process_sync_task({
    'source_platform': 'feishu',
    'target_platform': 'notion',
    'source_id': 'doc_id_here'
})
"
```

### Environment Setup
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API credentials
nano .env  # or vim .env

# Required environment variables:
# - FEISHU_APP_ID: Feishu app ID
# - FEISHU_APP_SECRET: Feishu app secret  
# - NOTION_TOKEN: Notion integration token
# - QINIU_ACCESS_KEY: Qiniu cloud access key
# - QINIU_SECRET_KEY: Qiniu cloud secret key
# - QINIU_BUCKET: Qiniu bucket name
# - QINIU_CDN_DOMAIN: Qiniu CDN domain URL
# - SECRET_KEY: Flask secret key for sessions
# - DATABASE_URL: Database connection URL (optional, defaults to SQLite)
# - LOG_LEVEL: Logging level (INFO, DEBUG, WARNING, ERROR)
# - MAX_SYNC_RETRIES: Maximum retry attempts for failed syncs (default: 3)
# - SYNC_TIMEOUT_SECONDS: Timeout for sync operations (default: 300)
```

### Static Assets Management
```bash
# Check static file structure
ls -la static/css/
ls -la static/js/
ls -la static/images/

# Verify frontend assets are loading
curl http://localhost:5000/static/css/main.css
curl http://localhost:5000/static/js/app.js
```

## Documentation System

The project maintains comprehensive documentation in the `docs/` directory:

```bash
# View complete documentation index
cat docs/DOCUMENTATION_INDEX.md

# Access main project documentation
cat docs/README.md

# Check project structure guide
cat docs/PROJECT_STRUCTURE.md

# Review API development guides
cat docs/API_OPTIMIZATION_COMPLETE.md
cat docs/FRONTEND_ARCHITECTURE_GUIDE.md
```

## Architecture

### Application Structure
The application follows a modular Flask architecture with clear separation of concerns:

- **Entry Point**: `app.py` - Main application entry using Flask factory pattern
- **Core Factory**: `app/core/app_factory.py` - Creates and configures Flask app instance
- **Background Processing**: `app/core/task_processor.py` - Thread-based sync task processor
- **API Layer**: RESTful endpoints organized by version (`/api/v1/`)
- **Service Layer**: Business logic for Feishu, Notion, and sync processing
- **Data Layer**: SQLAlchemy ORM models with Alembic migrations
- **Web Layer**: HTML templates with vanilla JavaScript for UI
- **Utilities**: Common helpers, decorators, and validation schemas

### Key Components

#### 1. Flask Application Factory (`app/core/app_factory.py`)
- Creates Flask app with proper configuration
- Registers blueprints for web and API routes
- Configures logging with rotating file handlers
- Sets up signal handlers for graceful shutdown
- Initializes database connections

#### 2. Database Layer (`database/`)
- **connection.py**: SQLAlchemy engine and session management with Python 3.6 compatibility
- **models.py**: ORM models (SyncRecord, SyncConfig, ImageMapping) with optimized indexing
- **migration_service.py**: Migrates from old raw SQLite to SQLAlchemy
- **query_optimizer.py**: Database query optimization utilities
- Uses Alembic for schema migrations
- Supports both SQLite (default) and MySQL databases

#### 3. API Endpoints (`app/api/v1/`)
- **sync_routes.py**: Sync configuration and manual trigger endpoints
- **monitoring_routes.py**: System status and statistics  
- **config_routes.py**: CRUD operations for sync configurations
- **settings_routes.py**: Application settings management
- **main.py**: Main API blueprint registration
- All endpoints return JSON with consistent structure
- RESTful design with proper HTTP status codes

#### 4. Service Layer (`app/services/`)
- **feishu_client.py**: Feishu API integration (document fetching, webhook handling)
- **notion_client.py**: Notion API integration (page creation/update)
- **qiniu_client.py**: Image upload to Qiniu Cloud CDN
- **sync_processor.py**: Core sync logic and task processing
- **sync_service.py**: High-level sync orchestration
- **document_service.py**: Document format conversion
- **monitoring_service.py**: System monitoring and metrics
- **sync_service_legacy.py**: Legacy sync service (deprecated)
- **document_service_legacy.py**: Legacy document service (deprecated)

#### 5. Background Task Processing
- `app/core/task_processor.py`: Runs sync tasks in background thread
- Checks for pending tasks every 30 seconds
- Handles task retry logic for failed syncs
- Thread-safe with proper locking mechanisms
- Processes up to 5 pending tasks per cycle

#### 6. Utilities and Helpers (`app/utils/`)
- **decorators.py**: Custom decorators for API endpoints
- **helpers.py**: Common utility functions and datetime formatting
- **schemas.py**: Data validation schemas using Pydantic/Marshmallow

#### 7. Web Interface (`app/web/`)
- **main.py**: Main web routes and dashboard
- **admin.py**: Administrative interface
- Uses vanilla JavaScript with no build process required
- Templates located in `templates/` directory with modern responsive design

### Sync Flow
1. **Webhook Trigger**: Feishu sends webhook on document change
2. **Task Creation**: System creates pending sync record
3. **Task Processing**: Background processor picks up pending tasks
4. **Content Fetch**: Fetches document content from source platform
5. **Format Conversion**: Converts between Feishu and Notion formats
6. **Image Processing**: Uploads images to Qiniu CDN
7. **Target Update**: Updates content in target platform
8. **Status Update**: Marks sync record as success/failed

### Key Design Decisions
- **No Build Process**: Pure Python Flask app, no frontend build needed
- **SQLite Default**: Uses SQLite for simplicity, supports MySQL via config
- **Thread-Based Processing**: Uses threads instead of Celery for simplicity
- **Vanilla JavaScript**: No frontend framework, keeps it simple
- **Blueprint Architecture**: Modular routing for easy extension
- **Environment Config**: All secrets in .env file
- **Python 3.6 Compatibility**: Custom datetime handling for older Python versions
- **Unified HTTP Client**: Uses httpx throughout for consistency
- **Configuration Management**: Centralized settings in `config/settings.py` with environment validation
- **Comprehensive Documentation**: Extensive docs system with specialized guides for different aspects

## Important Notes

### Deprecated Components
- **Dashboard Route**: `/dashboard` is deprecated, use main `/` route
- **Raw SQLite Code**: `app/core/database.py` deprecated in favor of SQLAlchemy
- **Production Server**: `production_server.py` deprecated, use `app.py`
- **Legacy API Files**: `app/api/dashboard.py`, `app/api/sync.py`, `app/api/webhook.py` removed
- **Legacy Services**: `sync_services.py` removed in favor of modular service architecture

### Migration Status (as of 2025-07-07)
- ✅ Migrated from raw SQLite to SQLAlchemy ORM
- ✅ Unified HTTP client to use httpx everywhere
- ✅ Fixed hardcoded paths to use dynamic PROJECT_ROOT
- ✅ Added Alembic for database migrations
- ✅ Cleaned up redundant dependencies
- ✅ Added Python 3.6 compatibility for datetime handling
- ✅ Improved database indexing for better query performance
- ✅ Added comprehensive utilities and helper functions
- ✅ Implemented Flask application factory pattern
- ✅ Added background task processor with thread-based processing
- ✅ Reorganized API endpoints into versioned blueprints (/api/v1/)
- ✅ Enhanced monitoring and health check endpoints
- ✅ Added comprehensive documentation in docs/ directory

### Security Considerations
- Webhook signatures verified for Feishu events
- API keys stored in environment variables
- Input validation on all endpoints
- HTTPS enforced in production via Nginx

### Common Issues and Solutions

1. **Database Locked Error**
   ```bash
   # Check file permissions
   ls -la feishu_notion_sync.db
   chmod 664 feishu_notion_sync.db
   
   # Restart service
   pkill -f "python app.py"
   python app.py
   ```

2. **Sync Task Not Processing**
   ```bash
   # Check task processor status
   tail -f app.log | grep "Task processor"
   
   # Manually trigger processing
   python -c "from app.core.task_processor import start_task_processor; start_task_processor()"
   ```

3. **Image Upload Failures**
   - Verify Qiniu credentials in .env
   - Check CDN domain is accessible
   - Ensure image size < 10MB

4. **Webhook Verification Failed**
   - Ensure webhook URL is correctly configured in Feishu app
   - Check FEISHU_APP_SECRET is correct
   - Verify server time is synchronized (for signature validation)

### API Usage Examples

```bash
# Create sync configuration
curl -X POST http://localhost:5000/api/v1/sync/configs \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "feishu",
    "document_id": "doccnXXXXXX",
    "sync_direction": "feishu_to_notion",
    "auto_sync": true
  }'

# Trigger manual sync
curl -X POST http://localhost:5000/api/v1/sync/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "source_platform": "feishu",
    "target_platform": "notion",
    "source_id": "doccnXXXXXX"
  }'

# Get sync history
curl http://localhost:5000/api/v1/sync/records?limit=10

# Get system status and monitoring dashboard
curl http://localhost:5000/api/v1/monitoring/dashboard

# Check application health
curl http://localhost:5000/health

# Get sync configurations
curl http://localhost:5000/api/v1/sync/configs

# Get application settings
curl http://localhost:5000/api/v1/settings
```

## 项目开发进度更新

### 当前版本: v2.4.5 (2025-07-11)

#### 最新完成的功能优化

**1. 前端分页系统重构 (2025-07-11)**
- 修复分页控件点击事件失效问题
- 优化事件绑定机制，防止重复绑定
- 统一分页按钮状态管理逻辑
- 添加详细的调试日志支持

**2. UI界面优化 (2025-07-11)**
- 移除右下角版本历史悬浮球干扰元素
- 清理分页按钮箭头符号，改为纯文本显示
- 修复侧边栏底部信息与分页控件重叠问题
- 优化页面层级管理，建立清晰的z-index体系

**3. 布局响应式改进 (2025-07-11)**
- 为所有页面内容添加适当的底部边距
- 分页控件增加白色背景、阴影和边框
- 确保在不同屏幕尺寸下UI元素不重叠
- 优化数据管理页面的空间布局

#### 技术债务清理

**1. 代码清理**
- 移除废弃的悬浮球相关HTML、CSS和JavaScript代码
- 清理未使用的CSS规则和变量
- 优化事件绑定逻辑，避免内存泄漏

**2. 调试能力增强**
- 为关键交互添加console.log调试信息
- 改进错误处理和用户反馈机制
- 优化开发者工具友好性

### 重要知识库沉淀

#### 前端开发最佳实践

**1. 事件绑定防重复模式**
```javascript
// 使用data属性标记防止重复绑定
if (!element.hasAttribute('data-listener-bound')) {
    element.addEventListener('event', handler);
    element.setAttribute('data-listener-bound', 'true');
}
```

**2. 分页组件标准化**
```javascript
// 统一的分页状态管理
function updatePaginationButtons(currentPage, totalPages) {
    // 按钮状态统一管理
    // 支持禁用状态和视觉反馈
}

// 调试友好的事件处理
button.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('交互调试信息');
    // 业务逻辑处理
});
```

**3. CSS层级管理规范**
```css
/* 推荐的z-index层级体系 */
/* 基础层级 */
.sidebar { z-index: 10; }
.main-content { z-index: 15; }

/* 交互层级 */
.pagination-controls { z-index: 20; }
.dropdown-menus { z-index: 25; }

/* 覆盖层级 */
.modals { z-index: 50; }
.notifications { z-index: 50; }
.tooltips { z-index: 60; }
```

#### 常见问题解决方案

**1. 模板缓存问题**
- 症状：修改HTML模板后页面未更新
- 解决：重启Flask应用或使用模板缓存禁用
- 预防：开发环境配置模板自动重载

**2. 事件绑定失效**
- 症状：按钮点击无响应
- 排查：检查DOM加载时机、事件冒泡、元素遮挡
- 解决：使用事件委托、添加调试日志、检查z-index

**3. 布局重叠问题**
- 症状：UI元素相互遮挡
- 排查：检查position、z-index、margin/padding
- 解决：建立层级体系、适当的间距、响应式设计

### 下一步开发计划

#### 短期目标 (1-2周)
1. **性能优化**
   - 前端代码压缩和优化
   - API响应时间优化
   - 数据库查询优化

2. **用户体验改进**
   - 加载状态指示器
   - 错误提示优化
   - 操作确认机制

#### 中期目标 (1个月)
1. **功能扩展**
   - 批量操作功能
   - 高级搜索和过滤
   - 导出功能完善

2. **系统稳定性**
   - 单元测试覆盖
   - 集成测试完善
   - 监控告警系统

#### 长期目标 (3个月)
1. **架构升级**
   - 微服务架构探索
   - 容器化部署
   - 水平扩展支持

2. **新功能开发**
   - 多租户支持
   - 权限管理系统
   - 数据分析报表

### 技术选型建议

#### 前端技术栈
- **当前**: Vanilla JavaScript + Tailwind CSS
- **建议**: 保持轻量级，避免过度工程化
- **考虑**: 引入TypeScript提高代码质量

#### 后端架构
- **当前**: Flask + SQLAlchemy + SQLite
- **建议**: 保持简洁，按需扩展
- **考虑**: 数据库迁移到PostgreSQL或MySQL

#### 部署和运维
- **当前**: 直接部署
- **建议**: 引入Docker容器化
- **考虑**: CI/CD自动化部署

---

## 重要提醒

1. **代码质量**: 所有新功能开发都应遵循已建立的最佳实践
2. **测试覆盖**: 关键功能必须有相应的测试用例
3. **文档更新**: 重要变更需要及时更新文档
4. **性能监控**: 定期检查系统性能指标
5. **安全考虑**: 所有输入验证和权限检查不能忽视