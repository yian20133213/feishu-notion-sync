# AI开发提示词：飞书-Notion双向同步系统

## 背景说明
你是一位资深的Python后端开发工程师，现在需要基于已完成的需求分析和技术设计，开发一个飞书-Notion双向同步系统。所有前期的需求分析、技术选型、架构设计都已完成，现在直接进入开发阶段。

## 项目基本信息

### 核心目标
开发一个自动化的飞书与Notion内容双向同步系统，支持：
- 飞书文档/表格 ↔ Notion页面/数据库
- 自动图片处理和存储优化
- Web管理界面和状态监控

### 技术架构
```
飞书平台 ↔ 同步服务(Python+FastAPI) ↔ Notion平台
                    ↓
              七牛云存储(图片CDN)
```

### 同步策略
- **飞书→Notion**：实时自动同步（Webhook触发）
- **Notion→飞书**：手动确认同步（Web界面操作）
- **内容格式**：统一使用Markdown作为中间格式
- **图片处理**：自动上传到七牛云，生成CDN链接

## 技术规格

### 技术栈
- **后端框架**：Python 3.x + FastAPI
- **数据库**：MySQL
- **图片存储**：七牛云对象存储
- **前端界面**：简单的HTML+JavaScript（管理后台）
- **部署环境**：Linux + Nginx + 宝塔面板

### 服务器环境
- **服务器**：腾讯云Linux服务器
- **部署路径**：/www/wwwroot/sync.yianlu.com/
- **域名**：sync.yianlu.com（已配置SSL和反向代理）
- **端口**：Flask运行在5000端口，Nginx反向代理

### API配置信息
```python
# 配置信息（开发时使用环境变量）
FEISHU_APP_ID = "cli_a8d295d399a25013"
FEISHU_APP_SECRET = "FTb3GlyUZlzFF6AK01k0mdtq03SpET7n"
NOTION_TOKEN = "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"
QINIU_ACCESS_KEY = "quisBFRU_RPX6-fO04_UrfMBukZLs1ofUDyBvgoZ"
QINIU_SECRET_KEY = "IeiMby-g2i2V4qYfkot4k41B7Ztd8o8N6YHC8NAf"
QINIU_BUCKET = "feishu-notion-sync"
QINIU_CDN_DOMAIN = "https://cdn.yianlu.com"
```

### 数据库设计
```sql
-- 同步记录表
CREATE TABLE sync_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    source_platform VARCHAR(20) NOT NULL,
    target_platform VARCHAR(20) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    target_id VARCHAR(100),
    content_type VARCHAR(20) NOT NULL,
    sync_status VARCHAR(20) NOT NULL,
    last_sync_time TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 图片映射表
CREATE TABLE image_mappings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    original_url VARCHAR(500) NOT NULL,
    qiniu_url VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_size INT NOT NULL,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INT DEFAULT 0,
    INDEX idx_original_url (original_url),
    INDEX idx_file_hash (file_hash)
);

-- 同步配置表
CREATE TABLE sync_configs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    platform VARCHAR(20) NOT NULL,
    document_id VARCHAR(100) NOT NULL,
    is_sync_enabled BOOLEAN DEFAULT TRUE,
    sync_direction VARCHAR(20) NOT NULL,
    auto_sync BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 功能需求

### 核心功能模块
1. **飞书API集成**：文档读取、事件处理
2. **Notion API集成**：页面创建、内容更新
3. **图片处理模块**：下载、压缩、上传、URL替换
4. **同步引擎**：格式转换、冲突处理
5. **Web管理界面**：配置管理、状态监控
6. **Webhook服务**：实时事件接收

### API接口设计
```
POST /webhook/feishu          # 飞书事件接收
GET  /api/sync/status         # 同步状态查询
POST /api/sync/trigger        # 手动触发同步
GET  /api/sync/history        # 同步历史记录
POST /api/sync/config         # 更新同步配置
GET  /api/dashboard           # 管理仪表板
GET  /health                  # 健康检查
```

### 图片处理要求
- **格式转换**：自动转为WebP格式，压缩比70%
- **去重机制**：MD5校验，相同图片只存储一份
- **错误处理**：下载失败时的降级处理
- **访问统计**：记录图片访问次数

## 开发要求

### 代码质量要求
- **结构清晰**：模块化设计，职责分离
- **错误处理**：完善的异常捕获和错误日志
- **配置管理**：使用环境变量管理敏感信息
- **日志记录**：详细的操作日志，便于调试

### 性能要求
- **异步处理**：使用async/await处理IO密集任务
- **并发控制**：限制同时处理的同步任务数量
- **缓存策略**：缓存频繁访问的API数据
- **资源释放**：及时释放文件句柄和网络连接

### 部署要求
- **环境隔离**：开发/测试/生产环境配置分离
- **进程管理**：使用systemd或supervisor管理进程
- **日志轮转**：自动轮转日志文件
- **监控集成**：提供健康检查接口

## 开发任务流

### 第一阶段：基础架构搭建
1. **项目初始化**
   - 创建项目目录结构
   - 配置虚拟环境和依赖
   - 设置配置文件和环境变量

2. **数据库初始化**
   - 创建数据库连接
   - 执行建表SQL
   - 实现基础的CRUD操作

3. **API客户端封装**
   - 飞书API客户端类
   - Notion API客户端类
   - 七牛云存储客户端类

### 第二阶段：核心功能开发
1. **图片处理模块**
   - 图片下载和压缩功能
   - 七牛云上传和URL生成
   - 图片映射关系管理

2. **内容格式转换**
   - 飞书富文本到Markdown转换
   - Markdown到Notion Block转换
   - 图片链接替换处理

3. **同步引擎核心**
   - 同步任务调度器
   - 冲突检测和处理
   - 状态跟踪和更新

### 第三阶段：接口和界面开发
1. **Webhook服务**
   - 飞书事件接收和验证
   - 事件分发和处理
   - 安全验证机制

2. **RESTful API**
   - 同步管理接口
   - 配置管理接口
   - 状态查询接口

3. **Web管理界面**
   - 简单的HTML管理后台
   - 同步状态显示
   - 配置管理表单

### 第四阶段：测试和优化
1. **功能测试**
   - 单元测试编写
   - 集成测试验证
   - 性能压力测试

2. **部署和配置**
   - 生产环境部署
   - 服务进程管理
   - 日志和监控配置

## 开发指导原则

### 敏捷开发模式
- **快速迭代**：每个功能模块独立开发和测试
- **持续集成**：代码提交后立即测试验证
- **用户反馈**：及时收集使用反馈并优化

### 错误处理策略
- **优雅降级**：API调用失败时的备用方案
- **重试机制**：网络异常时的自动重试
- **日志记录**：详细记录错误信息和调用栈

### 安全考虑
- **API密钥保护**：使用环境变量存储敏感信息
- **请求验证**：验证Webhook请求的合法性
- **访问控制**：Web界面的基础认证机制

## 测试策略

### 测试用例设计
1. **API集成测试**：验证各平台API调用正常
2. **图片处理测试**：验证图片下载、压缩、上传流程
3. **同步功能测试**：验证内容同步的准确性
4. **错误处理测试**：验证异常情况的处理机制

### 性能测试
- **并发处理**：模拟多个同步任务并发执行
- **内存使用**：监控内存占用和释放
- **响应时间**：测试API接口响应时间

## 开发环境配置

### 开发工具
- **代码编辑器**：VSCode或PyCharm
- **版本控制**：Git
- **依赖管理**：pip + requirements.txt
- **数据库工具**：MySQL Workbench或命令行

### 调试和监控
- **日志级别**：DEBUG（开发）/INFO（生产）
- **错误追踪**：详细的异常堆栈信息
- **性能监控**：API调用时间统计

## 交付标准

### 代码质量
- **代码规范**：遵循PEP8编码规范
- **注释完整**：关键函数和类有详细注释
- **测试覆盖**：核心功能有对应的测试用例

### 文档完善
- **API文档**：详细的接口说明和示例
- **部署文档**：完整的部署和配置指南
- **用户手册**：Web界面的使用说明

### 系统稳定性
- **容错处理**：各种异常情况的处理机制
- **性能稳定**：长期运行不出现内存泄漏
- **监控完善**：关键指标的监控和告警

---

## 开始开发

现在你可以开始基于以上背景信息进行开发。请按照任务流顺序进行，每完成一个阶段后继续下一个阶段，直到整个系统开发完成。

你有SSH访问权限，可以直接在服务器上进行开发、测试和部署。请开始第一阶段的开发工作。