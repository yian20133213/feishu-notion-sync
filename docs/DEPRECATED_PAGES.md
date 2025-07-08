# 废弃页面文档 / Deprecated Pages Documentation

## 📋 概述 / Overview

本文档记录了项目中已废弃的页面和功能，以及相关的开发规范。所有开发者在进行功能开发时必须遵循这些规定。

## ⚠️ 废弃页面列表 / Deprecated Pages List

### 1. `/dashboard` 页面 - 已废弃

**废弃时间**: 2025-06-28  
**废弃原因**: 功能分散，用户体验不一致  
**替代方案**: 主页 `/` 路由  

#### 禁止操作 / Prohibited Actions

❌ **严格禁止** 在 `/dashboard` 页面添加以下功能：
- 新建配置功能 (New Config)
- 手动同步功能 (Manual Sync)  
- 批量同步功能 (Batch Sync)
- 配置管理功能 (Config Management)
- 数据管理功能 (Data Management)
- 系统设置功能 (System Settings)
- 监控功能 (Monitoring)
- 任何业务逻辑功能

#### 当前状态 / Current Status

- ✅ 页面路由保留（向后兼容）
- ✅ 添加废弃警告注释
- ✅ 重定向到主页或显示废弃提示
- ❌ 不包含任何业务功能

#### 代码位置 / Code Locations

1. **后端路由**: `production_server.py:559-571`
   ```python
   @app.route('/dashboard')
   def old_dashboard():
       """⚠️ 废弃页面 - 不要在此页面添加任何功能 ⚠️"""
   ```

2. **前端调用**: `static/js/app.js:275`
   ```javascript
   // ⚠️ 注意：此处调用的是 /api/dashboard，不是 /dashboard 页面路由
   // /dashboard 页面路由已废弃，不要在该页面添加任何功能！
   ```

3. **模板文件**: `templates/dashboard.html` (如果存在)

## 🔧 开发规范 / Development Guidelines

### 功能开发位置 / Feature Development Location

**✅ 正确位置**：
- **主页路由**: `/` - 所有核心功能
- **API路由**: `/api/*` - 所有API接口
- **静态资源**: `/static/*` - CSS/JS/图片等

**❌ 错误位置**：
- **废弃页面**: `/dashboard` - 禁止添加任何功能

### API vs 页面路由区分 / API vs Page Route Distinction

**重要提醒**：请区分API路由和页面路由

| 类型 | 路径示例 | 用途 | 状态 |
|------|----------|------|------|
| 页面路由 | `/dashboard` | 渲染HTML页面 | ❌ 已废弃 |
| API路由 | `/api/dashboard` | 返回JSON数据 | ✅ 正常使用 |
| 页面路由 | `/` | 渲染主页 | ✅ 主要功能页面 |
| API路由 | `/api/sync/configs` | 配置管理API | ✅ 正常使用 |

### 新功能开发流程 / New Feature Development Process

1. **需求分析**: 确认功能属于哪个模块
2. **位置选择**: 在主页 `/` 相应区域开发
3. **API设计**: 使用 `/api/*` 路径设计API
4. **前端实现**: 在 `static/js/app.js` 中实现
5. **测试验证**: 确保功能完整可用

### 代码审查要点 / Code Review Checklist

在代码审查时，请检查以下要点：

- [ ] 新功能是否在主页 `/` 实现？
- [ ] 是否误在 `/dashboard` 页面添加功能？
- [ ] API路径是否使用 `/api/*` 格式？
- [ ] 是否添加了适当的废弃警告注释？
- [ ] 功能是否与现有模块保持一致？

## 📚 相关文档 / Related Documentation

- [README.md](./README.md) - 项目主文档
- [API_OPTIMIZATION_COMPLETE.md](./API_OPTIMIZATION_COMPLETE.md) - API优化文档
- [UI_DESIGN_GUIDE.md](./UI_DESIGN_GUIDE.md) - UI设计指南

## 🔄 版本历史 / Version History

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2025-06-28 | 初始版本，记录 `/dashboard` 页面废弃决定 |

## 📞 联系方式 / Contact

如有疑问或需要澄清，请联系项目维护者。

---

**⚠️ 重要提醒**: 本文档是项目开发的重要指导文件，所有开发者必须严格遵循其中的规定。违反这些规定可能导致代码审查不通过或功能回滚。 