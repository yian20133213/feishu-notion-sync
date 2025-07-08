# Notion分类选择功能说明

## 功能概述

本功能允许用户在创建飞书到Notion的同步配置时，选择目标Notion数据库中的特定分类（category），确保同步的内容能够正确分类到指定的类别中。

## 主要特性

### 1. 前端界面增强
- 在"新建同步配置"对话框中新增了"Notion分类"选择下拉框
- 仅在同步方向为"飞书 → Notion"或"双向同步"时显示分类选择
- 自动从Notion API获取可用的分类选项
- 提供默认分类选项作为后备方案

### 2. API端点扩展
- `GET /api/v1/notion/categories` - 获取Notion数据库的分类选项
- `POST /api/v1/sync/configs` - 创建配置时支持`notion_category`参数
- `PATCH /api/v1/sync/configs/<id>` - 更新配置时支持修改分类

### 3. 数据库模型更新
- 在`sync_configs`表中新增`notion_category`字段
- 支持存储用户选择的分类信息

### 4. 同步逻辑优化
- 同步处理器会根据配置中的分类设置自动应用到Notion页面
- 如果未指定分类，使用默认的"技术分享"分类

## 使用方法

### 创建新的同步配置
1. 点击"新建配置"按钮
2. 选择源平台为"飞书"
3. 输入飞书文档ID
4. 选择同步方向为"飞书 → Notion"或"双向同步"
5. 在出现的"Notion分类"下拉框中选择目标分类
6. 点击"创建配置"

### 手动同步时选择分类
1. 点击"手动同步"按钮
2. 输入要同步的文档ID或链接
3. 选择源平台和目标平台
4. 当目标平台为"Notion"时，会显示"Notion分类"选择框
5. 选择要同步到的分类
6. 点击"立即执行同步"

### 修改现有配置的分类
1. 在配置列表中找到要修改的配置
2. 点击"编辑"按钮
3. 修改"Notion分类"选择
4. 保存更改

## 技术实现

### 前端JavaScript
- `loadNotionCategories()` - 从API加载分类数据
- `toggleNotionCategorySection()` - 控制分类选择区域显示/隐藏
- 修改了`submitConfigForm()`以包含分类信息

### 后端API
- `NotionClient.get_database_properties()` - 获取Notion数据库属性和分类选项
- `SyncService.create_sync_config()` - 支持保存分类配置
- `SyncProcessor._get_notion_category_for_document()` - 获取文档的分类配置

### 数据库架构
```sql
ALTER TABLE sync_configs ADD COLUMN notion_category VARCHAR(50);
```

## 配置要求

### 环境变量
确保以下环境变量已正确配置：
- `NOTION_TOKEN` - Notion集成令牌
- `NOTION_DATABASE_ID` - 默认的Notion数据库ID（可选）

### Notion数据库结构
目标Notion数据库应包含以下属性：
- `title` - 标题（必需）
- `category` - 分类（单选类型）
- `type` - 类型（单选类型）
- `status` - 状态（单选类型）

## 默认分类选项

如果无法从Notion API获取分类选项，系统会提供以下默认选项：
- 技术分享
- Post
- Menu
- 同步文档

## 故障排除

### 分类选项无法加载
1. 检查Notion API令牌是否有效
2. 确认Notion数据库ID是否正确
3. 验证数据库权限设置
4. 查看浏览器控制台错误信息

### 同步时分类未生效
1. 确认配置中已保存分类信息
2. 检查Notion数据库是否有对应的分类选项
3. 查看同步日志获取详细错误信息

## 更新日志

### v2.4.1 (2025-01-05)
- ✅ 新增Notion分类选择功能
- ✅ 前端界面支持动态分类选择
- ✅ API支持获取和设置分类
- ✅ 数据库模型支持分类存储
- ✅ 同步逻辑支持指定分类创建