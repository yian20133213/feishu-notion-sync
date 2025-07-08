#!/usr/bin/env python3
"""
配置相关API路由 - 处理同步配置管理
"""
from flask import request, current_app
from app.utils import APIResponse, validate_json, paginated
from app.services import SyncService


def register_routes(bp):
    """注册配置相关路由到蓝图"""
    
    @bp.route('/sync/configs', methods=['GET'])
    @paginated(max_per_page=50)
    def get_sync_configs():
        """获取同步配置列表"""
        try:
            from flask import g
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.get_sync_configs(g.pagination['page'], g.pagination['per_page'])
            return APIResponse.success(result)
            
        except Exception as e:
            return APIResponse.error(f"获取配置列表失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/configs', methods=['POST'])
    @validate_json(['platform', 'document_id', 'sync_direction'])
    def create_sync_config():
        """创建同步配置"""
        try:
            data = request.get_json() or {}
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.create_sync_config(data)
            return APIResponse.success(result, meta={"created_id": result.get("config_id")})
            
        except ValueError as e:
            # 业务逻辑错误（如无效参数、配置已存在等）
            error_code = "VALIDATION_ERROR"
            status_code = 400
            if "已存在" in str(e):
                error_code = "CONFIG_EXISTS"
                status_code = 409
            return APIResponse.error(str(e), error_code, status_code=status_code)
        except Exception as e:
            return APIResponse.error(f"创建配置失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/configs/<int:config_id>', methods=['PATCH'])
    @validate_json()
    def patch_sync_config(config_id):
        """部分更新同步配置（如启用/禁用）"""
        try:
            data = request.get_json()
            
            if not data:
                return APIResponse.error("没有提供要更新的字段", "NO_FIELDS_TO_UPDATE", status_code=400)
            
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.update_sync_config(config_id, data)
            return APIResponse.success(result)
            
        except ValueError as e:
            error_code = "VALIDATION_ERROR"
            status_code = 400
            if "不存在" in str(e):
                error_code = "CONFIG_NOT_FOUND"
                status_code = 404
            return APIResponse.error(str(e), error_code, status_code=status_code)
        except Exception as e:
            return APIResponse.error(f"更新配置失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/config/<int:config_id>', methods=['GET'])
    def get_sync_config(config_id):
        """获取单个同步配置"""
        try:
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.get_sync_config_by_id(config_id)
            if not result:
                return APIResponse.error("配置不存在", "CONFIG_NOT_FOUND", status_code=404)
            
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取配置失败: {str(e)}", "GET_CONFIG_ERROR", status_code=500)

    @bp.route('/sync/config/<int:config_id>/toggle', methods=['POST'])
    @validate_json(['enabled'])
    def toggle_sync_config(config_id):
        """切换同步配置状态"""
        try:
            data = request.get_json()
            enabled = data.get('enabled')
            
            sync_service = SyncService(logger=current_app.logger)
            update_data = {'is_sync_enabled': enabled}
            result = sync_service.update_sync_config(config_id, update_data)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "CONFIG_NOT_FOUND", status_code=404)
        except Exception as e:
            return APIResponse.error(f"切换配置状态失败: {str(e)}", "TOGGLE_CONFIG_ERROR", status_code=500)
    
    @bp.route('/notion/categories', methods=['GET'])
    def get_notion_categories():
        """获取Notion数据库的分类选项"""
        try:
            from app.services.notion_client import NotionClient
            from config import settings
            
            # 获取默认的Notion数据库ID (这里需要配置)
            database_id = getattr(settings, 'notion_database_id', None)
            if not database_id:
                # 如果没有配置数据库ID，返回默认分类
                default_categories = ['技术分享', 'Post', 'Menu', '同步文档']
                return APIResponse.success({
                    'categories': default_categories,
                    'source': 'default'
                })
            
            notion_client = NotionClient()
            db_properties = notion_client.get_database_properties(database_id)
            
            return APIResponse.success({
                'categories': db_properties.get('categories', []),
                'types': db_properties.get('types', []),
                'database_title': db_properties.get('title', ''),
                'source': 'notion_api'
            })
            
        except Exception as e:
            current_app.logger.error(f"Failed to get Notion categories: {str(e)}")
            # 如果API调用失败，返回默认分类
            default_categories = ['技术分享', 'Post', 'Menu', '同步文档']
            return APIResponse.success({
                'categories': default_categories,
                'source': 'fallback'
            })

    @bp.route('/sync/config/<int:config_id>', methods=['DELETE'])
    def delete_sync_config(config_id):
        """删除同步配置"""
        try:
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.delete_sync_config(config_id)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "CONFIG_NOT_FOUND", status_code=404)
        except Exception as e:
            return APIResponse.error(f"删除配置失败: {str(e)}", "DELETE_CONFIG_ERROR", status_code=500)

    # 添加单数路径别名以保持与前端兼容性
    @bp.route('/sync/config', methods=['POST'])
    @validate_json(['platform', 'document_id', 'sync_direction'])
    def create_sync_config_singular():
        """创建同步配置（单数路径别名）"""
        return create_sync_config()

    @bp.route('/sync/config', methods=['GET'])
    @paginated(max_per_page=50)
    def get_sync_configs_singular():
        """获取同步配置列表（单数路径别名）"""
        return get_sync_configs()