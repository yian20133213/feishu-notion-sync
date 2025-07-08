# 📁 项目结构说明

## 🗂️ 目录结构

```
sync.yianlu.com/
├── README.md                           # 📋 项目简介（指向docs/）
├── docs/                               # 📚 完整文档目录
│   ├── README.md                       # 📖 详细项目说明
│   ├── DOCUMENTATION_INDEX.md          # 📚 文档索引导航
│   ├── API_OPTIMIZATION_COMPLETE.md    # 🚀 API优化完整指南
│   ├── API_MIGRATION_GUIDE.md          # 🔄 API迁移指南
│   ├── SYNC_WORKER_GUIDE.md            # ⚙️ 后台任务处理指南
│   ├── FRONTEND_ARCHITECTURE_GUIDE.md  # 🎨 前端架构设计指南
│   ├── FRONTEND_OPTIMIZATION_COMPLETE.md # 🛠️ 前端优化完整指南
│   ├── DEPRECATED_PAGES.md             # ⚠️ 废弃页面规范
│   ├── PROJECT_STRUCTURE.md            # 📁 项目结构说明（本文件）
│   └── 其他历史文档...                  # 📚 历史参考文档
├── app/                                # 🏗️ 应用核心模块
│   ├── api/                            # 🔌 API接口层
│   ├── services/                       # 🔧 业务服务层
│   ├── models/                         # 📊 数据模型
│   └── utils/                          # 🛠️ 工具函数
├── database/                           # 🗄️ 数据库相关
├── templates/                          # 🎨 前端模板
├── static/                             # 📦 静态资源
├── config/                             # ⚙️ 配置文件
├── production_server.py                # 🚀 生产服务器入口
├── requirements.txt                    # 📋 依赖列表
└── .env.example                        # 🔐 环境变量示例
```

## 📚 文档组织原则

### 1. **目录化管理**
- 所有文档统一放在 `docs/` 目录
- 项目根目录保持简洁，只有核心文件
- 便于版本控制和文档管理

### 2. **分类清晰**
- **API文档**: API优化、迁移指南
- **系统运维**: 后台任务、监控指南
- **前端文档**: 架构设计、优化指南
- **开发规范**: 废弃页面、开发规范
- **项目管理**: 文档索引、项目结构

### 3. **导航便利**
- `docs/DOCUMENTATION_INDEX.md` 作为总导航
- 根目录 `README.md` 提供快速链接
- 每个文档都有明确的用途说明

## 🎯 使用建议

### 新用户
1. 先阅读根目录 `README.md` 了解项目概况
2. 查看 `docs/README.md` 获取详细安装说明
3. 根据需要查阅相应的专门文档

### 开发者
1. 必读 `docs/DEPRECATED_PAGES.md` 了解开发规范
2. 参考 `docs/API_OPTIMIZATION_COMPLETE.md` 进行API开发
3. 前端开发参考 `docs/FRONTEND_ARCHITECTURE_GUIDE.md`

### 运维人员
1. 重点关注 `docs/SYNC_WORKER_GUIDE.md`
2. 参考 `docs/API_OPTIMIZATION_COMPLETE.md` 了解系统架构

## 📝 维护说明

### 文档更新
- 所有新文档都应放在 `docs/` 目录
- 更新后需同步更新 `docs/DOCUMENTATION_INDEX.md`
- 重要变更需在根目录 `README.md` 中体现

### 目录规范
- 文档文件使用英文命名，下划线分隔
- 历史文档保留但标注状态
- 定期清理过时或重复的文档

---

**📅 最后更新**: 2025-06-29  
**📝 维护者**: 开发团队 