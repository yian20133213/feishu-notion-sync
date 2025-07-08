# 🚀 飞书-Notion同步系统

一个现代化的飞书与Notion双向同步管理系统，提供实时数据同步、智能冲突处理和完善的监控功能。

## 📚 文档

完整的项目文档已移至 **`docs/`** 目录：

### 🎯 快速开始
- **[完整安装指南](docs/README.md)** - 详细的安装、配置和使用说明
- **[API优化指南](docs/API_OPTIMIZATION_COMPLETE.md)** - API技术核心文档
- **[开发规范](docs/DEPRECATED_PAGES.md)** - 必读的开发规范和注意事项

### 📖 技术文档
- **[文档索引](docs/DOCUMENTATION_INDEX.md)** - 所有文档的完整导航
- **[API迁移指南](docs/API_MIGRATION_GUIDE.md)** - 新旧API迁移说明
- **[后台任务指南](docs/SYNC_WORKER_GUIDE.md)** - 系统运维指南

### 🎨 前端文档
- **[前端架构指南](docs/FRONTEND_ARCHITECTURE_GUIDE.md)** - UI设计系统和架构
- **[前端优化指南](docs/FRONTEND_OPTIMIZATION_COMPLETE.md)** - 前端问题修复和优化

## ⚡ 快速启动

### 环境要求
- Python 3.6+
- SQLite 3.0+ (默认) 或 MySQL 5.7+

### 安装步骤

```bash
# 1. 克隆项目
git clone [repository-url]
cd sync.yianlu.com

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置以下必需变量：
# - FEISHU_APP_ID: 飞书应用ID
# - FEISHU_APP_SECRET: 飞书应用密钥
# - NOTION_TOKEN: Notion集成令牌
# - QINIU_ACCESS_KEY: 七牛云访问密钥
# - QINIU_SECRET_KEY: 七牛云秘密密钥
# - QINIU_BUCKET: 七牛云存储桶名
# - QINIU_CDN_DOMAIN: 七牛云CDN域名

# 5. 初始化数据库
python database/init_db.py

# 6. 启动服务
python app.py
```

### 运行模式

#### 开发模式
```bash
# 开发环境启动（调试模式）
python app.py
```

#### 生产模式
```bash
# 后台运行
nohup python app.py > server.log 2>&1 &

# 检查服务状态
ps aux | grep "python app.py"

# 健康检查
curl http://localhost:5000/health
```

#### 服务管理
```bash
# 停止服务
pkill -f "python app.py"

# 查看日志
tail -f server.log
tail -f app.log

# 重启服务
pkill -f "python app.py" && nohup python app.py > server.log 2>&1 &
```

### 数据库管理

```bash
# 使用Alembic进行数据库迁移
alembic init alembic                        # 初始化Alembic
alembic revision --autogenerate -m "描述"    # 创建迁移脚本
alembic upgrade head                        # 应用迁移

# 从旧SQLite迁移到新结构
python database/migration_service.py
```

### 访问地址
- **Web界面**: http://localhost:5000
- **API文档**: http://localhost:5000/api/v1/
- **健康检查**: http://localhost:5000/health
- **监控面板**: http://localhost:5000/api/v1/monitoring/dashboard

### 🔧 故障排除

#### 常见问题

1. **数据库锁定错误**
```bash
# 检查文件权限
ls -la feishu_notion_sync.db
chmod 664 feishu_notion_sync.db

# 重启服务
pkill -f "python app.py"
python app.py
```

2. **同步任务不处理**
```bash
# 检查任务处理器状态
tail -f app.log | grep "Task processor"

# 手动触发处理
python -c "from app.core.task_processor import start_task_processor; start_task_processor()"
```

3. **图片上传失败**
- 验证七牛云凭据配置
- 检查CDN域名可访问性
- 确保图片大小 < 10MB

4. **Webhook验证失败**
- 确保webhook URL正确配置
- 检查FEISHU_APP_SECRET正确性
- 验证服务器时间同步

#### 测试连接
```bash
# 测试数据库连接
python -c "from database.connection import db; print('Database:', db.test_connection())"

# 测试七牛云连接
python -c "from app.services.qiniu_client import QiniuClient; print('Qiniu:', QiniuClient().test_connection())"
```

## 🌟 主要功能

- ✅ **双向同步**: 飞书 ↔ Notion 实时数据同步
- ✅ **智能处理**: 自动冲突检测和解决
- ✅ **实时监控**: 完善的性能监控和日志系统
- ✅ **批量操作**: 支持大规模文档批量同步
- ✅ **图片处理**: 自动图片上传和CDN加速
- ✅ **Web界面**: 现代化的管理界面

## 📞 技术支持

- **完整文档**: 查看 [`docs/`](docs/) 目录
- **问题反馈**: 提交 GitHub Issue
- **技术讨论**: 联系开发团队

---

**📋 注意**: 本文件为简化版说明，完整文档请查看 [`docs/README.md`](docs/README.md) 