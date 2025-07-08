# 飞书-Notion双向同步系统 / Feishu-Notion Sync

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)

一个强大的飞书与Notion双向同步工具，支持自动内容同步、图片处理、格式转换和可视化管理界面。

A powerful bidirectional sync tool between Feishu (Lark) and Notion, featuring automatic content synchronization, image processing, format conversion, and visual management interface.

## ⚠️ 重要说明 / Important Notice

### 废弃页面警告 / Deprecated Page Warning

**🚨 `/dashboard` 页面已废弃，禁止添加任何功能！**

- ❌ **不要** 在 `/dashboard` 页面添加新建配置功能
- ❌ **不要** 在 `/dashboard` 页面添加手动同步功能  
- ❌ **不要** 在 `/dashboard` 页面添加批量同步功能
- ❌ **不要** 在 `/dashboard` 页面添加任何业务逻辑功能

**✅ 所有功能必须在主页 `/` 路由实现！**

此限制的原因：
1. 避免功能分散，提高用户体验一致性
2. 简化维护，所有功能集中在主页管理
3. 防止历史遗留问题影响新功能开发

**对于开发者**：
- 所有新功能开发请在主页 `/` 进行
- API调用使用 `/api/*` 路径，不要与页面路由混淆
- 如需修改现有功能，请在主页相应模块进行

## ✨ 主要特性 / Key Features

### 📋 内容同步 / Content Sync
- **双向同步**: 支持飞书↔Notion双向内容同步
- **实时同步**: 基于Webhook的实时自动同步
- **格式转换**: 智能转换飞书富文本到Notion块格式
- **内容完整性**: 保持文本、标题、列表、代码块等格式

### 🖼️ 图片处理 / Image Processing
- **自动上传**: 图片自动上传到七牛云CDN
- **格式优化**: 支持WebP格式和压缩优化
- **去重机制**: 基于MD5的图片去重
- **CDN加速**: 全球CDN加速访问

### 🎛️ 管理界面 / Management Interface
- **可视化仪表板**: 实时监控同步状态和统计
- **配置管理**: 图形化同步配置管理
- **历史记录**: 完整的同步历史和错误日志
- **批量操作**: 支持批量删除和状态筛选

### 🚀 手动同步 / Manual Sync
- **即时同步**: 支持立即触发同步操作
- **防重复提交**: 智能防重复提交机制
- **错误重试**: 自动重试失败的同步任务

## 🛠️ 技术栈 / Tech Stack

- **后端**: Python 3.6+ + Flask
- **数据库**: SQLite (生产可选MySQL)
- **前端**: Vanilla JavaScript + HTML5 + CSS3
- **存储**: 七牛云对象存储 + CDN
- **API集成**: 飞书开放平台 + Notion API

## 📦 快速开始 / Quick Start

### 1. 克隆项目 / Clone Repository
```bash
git clone https://github.com/yian20133213/feishu-notion-sync.git
cd feishu-notion-sync
```

### 2. 安装依赖 / Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量 / Configure Environment
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥
```

### 4. 初始化数据库 / Initialize Database
```bash
python database/init_db.py
```

### 5. 启动服务 / Start Service
```bash
# 开发环境
python production_server.py

# 生产环境（推荐使用进程管理器）
nohup python production_server.py > server.log 2>&1 &
```

### 6. 访问管理界面 / Access Dashboard
打开浏览器访问: `http://localhost:5000`

## ⚙️ 详细配置指南 / Detailed Configuration Guide

### 环境变量配置 / Environment Variables

创建 `.env` 文件并配置以下变量：

```bash
# 飞书API配置 / Feishu API Configuration
FEISHU_APP_ID=cli_a1234567890abcdef          # 飞书应用ID
FEISHU_APP_SECRET=1234567890abcdef123456     # 飞书应用密钥

# Notion API配置 / Notion API Configuration
NOTION_TOKEN=secret_1234567890abcdef         # Notion集成令牌

# 七牛云存储配置 / Qiniu Cloud Storage Configuration
QINIU_ACCESS_KEY=your_access_key_here        # 七牛云访问密钥
QINIU_SECRET_KEY=your_secret_key_here        # 七牛云安全密钥
QINIU_BUCKET=feishu-notion-sync              # 存储空间名称
QINIU_CDN_DOMAIN=https://cdn.example.com     # CDN加速域名

# 服务配置 / Service Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your_super_secret_key_here

# 数据库配置（可选MySQL）/ Database Configuration (Optional MySQL)
# DATABASE_URL=mysql://username:password@localhost/database_name

# 其他配置 / Other Configuration
LOG_LEVEL=INFO
MAX_SYNC_RETRIES=3
SYNC_TIMEOUT_SECONDS=300
```

## 🔑 飞书应用配置 / Feishu App Configuration

### 1. 创建飞书应用 / Create Feishu App

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录后点击 **"创建应用"**
3. 选择 **"企业自建应用"**
4. 填写应用基本信息：
   - **应用名称**: 飞书-Notion同步工具
   - **应用描述**: 用于同步飞书文档到Notion的工具
   - **应用图标**: 上传应用图标

### 2. 配置应用权限 / Configure App Permissions

在应用管理页面，找到 **"权限管理"** → **"权限配置"**，可以选择以下两种方式配置权限：

#### 方式一：JSON导入（推荐）
复制以下JSON配置并导入：

```json
{
  "scopes": {
    "tenant": [
      "bitable:app",
      "bitable:app:readonly",
      "docs:document.media:download",
      "docs:document:export",
      "docx:document",
      "docx:document:create",
      "docx:document:readonly",
      "drive:drive",
      "drive:drive.metadata:readonly",
      "im:message.group_at_msg:readonly",
      "wiki:member:create",
      "wiki:member:retrieve",
      "wiki:member:update",
      "wiki:node:copy",
      "wiki:node:create",
      "wiki:node:move",
      "wiki:node:read",
      "wiki:node:retrieve",
      "wiki:node:update",
      "wiki:setting:read",
      "wiki:setting:write_only",
      "wiki:space:read",
      "wiki:space:retrieve",
      "wiki:space:write_only",
      "wiki:wiki",
      "wiki:wiki:readonly"
    ],
    "user": [
      "docx:document",
      "docx:document:readonly",
      "drive:drive"
    ]
  }
}
```

#### 方式二：手动添加权限
在权限管理页面手动添加以下权限：

**应用级权限 (tenant)**:
- `bitable:app` - 多维表格应用权限
- `bitable:app:readonly` - 多维表格应用只读权限
- `docs:document.media:download` - 文档媒体下载权限
- `docs:document:export` - 文档导出权限
- `docx:document` - 新版文档权限
- `docx:document:create` - 新版文档创建权限
- `docx:document:readonly` - 新版文档只读权限
- `drive:drive` - 云空间权限
- `drive:drive.metadata:readonly` - 云空间元数据只读权限
- `wiki:member:*` - Wiki成员相关权限
- `wiki:node:*` - Wiki节点相关权限
- `wiki:setting:*` - Wiki设置相关权限
- `wiki:space:*` - Wiki空间相关权限
- `wiki:wiki*` - Wiki相关权限

**用户级权限 (user)**:
- `docx:document` - 新版文档权限
- `docx:document:readonly` - 新版文档只读权限
- `drive:drive` - 云空间权限

### 3. 配置事件订阅 / Configure Event Subscription

1. 在应用管理页面找到 **"事件订阅"**
2. 配置请求网址: `https://your-domain.com/webhook/feishu`
3. 添加需要的事件类型：
   - **文档变更事件**: `drive.file.updated_v1`
   - **文档创建事件**: `drive.file.created_v1`

### 4. 获取应用凭证 / Get App Credentials

1. 在 **"凭证与基础信息"** 页面获取：
   - **App ID**: 复制到 `FEISHU_APP_ID`
   - **App Secret**: 复制到 `FEISHU_APP_SECRET`

### 5. 发布应用 / Publish App

1. 完成配置后，点击 **"版本管理与发布"**
2. 创建版本并提交审核
3. 审核通过后即可正常使用

## 🔗 Notion集成配置 / Notion Integration Configuration

### 1. 创建Notion集成 / Create Notion Integration

1. 访问 [Notion Developers](https://www.notion.so/my-integrations)
2. 点击 **"New integration"**
3. 填写集成信息：
   - **Name**: Feishu Notion Sync
   - **Logo**: 上传集成图标
   - **Associated workspace**: 选择工作区

### 2. 获取集成令牌 / Get Integration Token

1. 创建完成后，复制 **"Internal Integration Token"**
2. 将令牌添加到 `.env` 文件的 `NOTION_TOKEN`

### 3. 配置权限 / Configure Permissions

确保集成具有以下权限：
- **Content Capabilities**:
  - ✅ Read content
  - ✅ Update content  
  - ✅ Insert content
- **Comment Capabilities**:
  - ✅ Read comments
  - ✅ Create comments
- **User Capabilities**:
  - ✅ Read user information

### 4. 分享页面给集成 / Share Pages with Integration

1. 打开需要同步的Notion页面
2. 点击页面右上角的 **"Share"**
3. 点击 **"Invite"** 并搜索你的集成名称
4. 选择集成并点击 **"Invite"**

## ☁️ 七牛云存储配置 / Qiniu Cloud Storage Configuration

### 1. 注册七牛云账号 / Register Qiniu Account

1. 访问 [七牛云官网](https://www.qiniu.com/)
2. 注册并完成实名认证

### 2. 创建存储空间 / Create Storage Bucket

1. 登录控制台，进入 **"对象存储"**
2. 点击 **"新建存储空间"**
3. 配置存储空间：
   - **存储空间名称**: `feishu-notion-sync`
   - **存储区域**: 选择合适的区域
   - **访问控制**: 公开空间

### 3. 获取密钥 / Get Access Keys

1. 进入 **"密钥管理"** 页面
2. 创建或查看现有密钥：
   - **AccessKey**: 复制到 `QINIU_ACCESS_KEY`
   - **SecretKey**: 复制到 `QINIU_SECRET_KEY`

### 4. 配置CDN加速域名 / Configure CDN Domain

1. 在存储空间管理页面，进入 **"域名管理"**
2. 添加自定义域名或使用测试域名
3. 配置HTTPS证书（推荐）
4. 将域名添加到 `.env` 的 `QINIU_CDN_DOMAIN`

## 🔌 API接口文档 / API Documentation

### 核心API端点 / Core API Endpoints

#### 同步配置管理 / Sync Configuration Management

```bash
# 获取所有同步配置
GET /api/sync/configs
Response: {
  "success": true,
  "data": [
    {
      "id": 1,
      "platform": "feishu",
      "document_id": "doc123",
      "sync_direction": "feishu_to_notion",
      "is_sync_enabled": true,
      "auto_sync": true,
      "created_at": "2023-06-01T10:00:00Z"
    }
  ]
}

# 创建同步配置
POST /api/sync/config
Content-Type: application/json
{
  "platform": "feishu",
  "document_id": "doc123",
  "sync_direction": "feishu_to_notion",
  "auto_sync": true,
  "is_sync_enabled": true
}

# 更新同步配置
PUT /api/sync/config/{id}
Content-Type: application/json
{
  "is_sync_enabled": false
}

# 删除同步配置
DELETE /api/sync/config/{id}

# 切换配置启用状态
POST /api/sync/config/{id}/toggle
```

#### 同步操作 / Sync Operations

```bash
# 手动触发同步
POST /api/sync/trigger
Content-Type: application/json
{
  "source_platform": "feishu",
  "target_platform": "notion",
  "source_id": "doc123",
  "content_type": "document"
}

# 获取同步记录（分页）
GET /api/sync/records?page=1&limit=20&status=success

# 获取同步历史（仪表板用）
GET /api/sync/history?limit=10

# 获取待处理任务
GET /api/sync/pending

# 获取失败任务
GET /api/sync/failed

# 重试失败的同步任务
POST /api/sync/retry/{record_id}
```

#### 图片管理 / Image Management

```bash
# 获取图片统计信息
GET /api/images/stats
Response: {
  "success": true,
  "data": {
    "total_images": 150,
    "total_size": "45.2MB",
    "qiniu_images": 145,
    "local_images": 5
  }
}

# 获取图片列表（分页）
GET /api/images?page=1&limit=20

# 批量删除图片记录
DELETE /api/images/batch
Content-Type: application/json
{
  "image_ids": [1, 2, 3, 4, 5]
}
```

#### 系统状态 / System Status

```bash
# 健康检查
GET /health
Response: {
  "status": "healthy",
  "timestamp": "2023-06-01T10:00:00Z",
  "version": "1.0.0"
}

# 获取仪表板数据
GET /api/dashboard
Response: {
  "success": true,
  "data": {
    "sync_stats": {
      "total": 100,
      "success": 95,
      "failed": 3,
      "pending": 2,
      "success_rate": 95.0
    },
    "recent_syncs": [...],
    "system_status": {
      "feishu_api": "connected",
      "notion_api": "connected",
      "qiniu_storage": "connected"
    }
  }
}
```

### Webhook端点 / Webhook Endpoints

```bash
# 飞书事件回调
POST /webhook/feishu
Content-Type: application/json
Headers:
  X-Lark-Request-Timestamp: {timestamp}
  X-Lark-Request-Nonce: {nonce}
  X-Lark-Signature: {signature}

# 处理各种飞书事件，如文档更新、创建等
```

## 🔍 使用示例 / Usage Examples

### 示例1: 创建同步配置

```bash
curl -X POST https://your-domain.com/api/sync/config \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "feishu",
    "document_id": "doccnAbCdEfGhIjKlMnOpQrS",
    "sync_direction": "feishu_to_notion",
    "auto_sync": true,
    "is_sync_enabled": true
  }'
```

### 示例2: 手动触发同步

```bash
curl -X POST https://your-domain.com/api/sync/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "source_platform": "feishu",
    "target_platform": "notion",
    "source_id": "doccnAbCdEfGhIjKlMnOpQrS",
    "content_type": "document"
  }'
```

### 示例3: 查看同步历史

```bash
curl https://your-domain.com/api/sync/history?limit=10
```

## 📊 项目结构 / Project Structure

```
feishu-notion-sync/
├── app/                    # 应用核心模块
│   ├── api/               # API接口层
│   │   ├── dashboard.py   # 仪表板API
│   │   ├── sync.py        # 同步相关API
│   │   └── webhook.py     # Webhook处理
│   ├── services/          # 业务服务层
│   │   ├── feishu_client.py    # 飞书API客户端
│   │   ├── notion_client.py    # Notion API客户端
│   │   ├── qiniu_client.py     # 七牛云客户端
│   │   └── sync_processor.py   # 同步处理器
│   └── models/            # 数据模型
│       ├── sync_config.py      # 同步配置模型
│       ├── sync_record.py      # 同步记录模型
│       └── image_mapping.py    # 图片映射模型
├── database/              # 数据库相关
│   ├── init_db.py        # 数据库初始化
│   ├── connection.py     # 数据库连接
│   └── models.py         # 数据模型定义
├── templates/             # 前端模板
│   └── dashboard.html    # 管理界面
├── static/               # 静态资源
│   └── images/           # 图片存储目录
├── production_server.py  # 生产服务器入口
├── requirements.txt      # 依赖列表
├── .env.example         # 环境变量示例
├── .gitignore           # Git忽略文件
└── README.md            # 项目说明文档
```

## 🐛 故障排查 / Troubleshooting

### 常见问题及解决方案 / Common Issues and Solutions

#### 1. 同步失败 / Sync Failed
```bash
# 检查API权限
curl -H "Authorization: Bearer ${FEISHU_ACCESS_TOKEN}" \
     https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal

# 检查Notion连接
curl -H "Authorization: Bearer ${NOTION_TOKEN}" \
     -H "Notion-Version: 2022-06-28" \
     https://api.notion.com/v1/users/me

# 查看错误日志
tail -f production_server.log
```

#### 2. 图片上传失败 / Image Upload Failed
```bash
# 检查七牛云配置
curl -X POST https://upload.qiniup.com/ \
  -F "token=${QINIU_UPLOAD_TOKEN}" \
  -F "file=@test.jpg"

# 验证CDN域名
curl -I https://your-cdn-domain.com/test-image.jpg
```

#### 3. 数据库锁定 / Database Locked
```bash
# 检查数据库文件权限
ls -la feishu_notion_sync.db

# 重启服务
pkill -f production_server.py
nohup python production_server.py > server.log 2>&1 &
```

#### 4. Webhook验证失败 / Webhook Verification Failed
```bash
# 检查飞书应用配置
# 确保Webhook URL正确: https://your-domain.com/webhook/feishu
# 确保事件订阅已启用

# 验证签名算法（如需要）
# 检查 X-Lark-Signature 头部计算是否正确
```

## 🚀 部署指南 / Deployment Guide

### 生产环境部署 / Production Deployment

#### 1. 使用Nginx反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 2. 使用Systemd服务管理

创建 `/etc/systemd/system/feishu-notion-sync.service`:

```ini
[Unit]
Description=Feishu Notion Sync Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/feishu-notion-sync
Environment=PYTHONPATH=/path/to/feishu-notion-sync
ExecStart=/usr/bin/python3 production_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable feishu-notion-sync
sudo systemctl start feishu-notion-sync
```

#### 3. 使用Docker部署

创建 `Dockerfile`:

```dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "production_server.py"]
```

创建 `docker-compose.yml`:

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

部署：
```bash
docker-compose up -d
```

## 📈 性能优化 / Performance Optimization

### 1. 数据库优化 / Database Optimization

```sql
-- 添加索引提升查询性能
CREATE INDEX idx_sync_records_status ON sync_records(sync_status);
CREATE INDEX idx_sync_records_created_at ON sync_records(created_at DESC);
CREATE INDEX idx_sync_records_composite ON sync_records(sync_status, created_at DESC);
CREATE INDEX idx_image_mappings_hash ON image_mappings(file_hash);
```

### 2. 缓存策略 / Caching Strategy

```python
# 使用Redis缓存频繁访问的数据
import redis
r = redis.Redis(host='localhost', port=6379, db=0)

# 缓存飞书访问令牌
def get_feishu_access_token():
    token = r.get('feishu_access_token')
    if not token:
        token = fetch_new_token()
        r.setex('feishu_access_token', 7200, token)  # 2小时过期
    return token
```

### 3. 异步处理 / Asynchronous Processing

```python
# 使用Celery处理耗时的同步任务
from celery import Celery

app = Celery('sync_tasks', broker='redis://localhost:6379')

@app.task
def process_sync_task(sync_config_id):
    # 异步处理同步任务
    pass
```

## 🔒 安全最佳实践 / Security Best Practices

### 1. API密钥管理 / API Key Management
- 使用环境变量存储敏感信息
- 定期轮换API密钥
- 限制API密钥权限范围

### 2. Webhook安全 / Webhook Security
- 验证Webhook签名
- 使用HTTPS传输
- 实现请求频率限制

### 3. 数据保护 / Data Protection
- 敏感数据加密存储
- 实现访问日志记录
- 定期备份重要数据

## 🤝 贡献指南 / Contributing

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证 / License

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 技术支持 / Support

- **问题反馈**: [GitHub Issues](https://github.com/yian20133213/feishu-notion-sync/issues)
- **功能建议**: [GitHub Discussions](https://github.com/yian20133213/feishu-notion-sync/discussions)
- **文档改进**: 欢迎提交PR改进文档

## 🎯 路线图 / Roadmap

- [ ] 支持更多内容类型（表格、数据库等）
- [ ] 多用户支持和权限管理
- [ ] 异步任务队列优化
- [ ] 更多第三方平台集成
- [ ] 移动端管理应用
- [ ] Docker一键部署
- [ ] 监控告警系统

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yian20133213/feishu-notion-sync&type=Date)](https://star-history.com/#yian20133213/feishu-notion-sync&Date)

---

**开发者**: [yian20133213](https://github.com/yian20133213)  
**最后更新**: 2025-06-23  
**项目地址**: https://github.com/yian20133213/feishu-notion-sync