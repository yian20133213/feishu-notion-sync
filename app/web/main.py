#!/usr/bin/env python3
"""
主Web页面蓝图 - 处理前端页面路由
"""
from flask import Blueprint, render_template, jsonify, request, current_app
from datetime import datetime
import logging

# 创建Web蓝图
main_bp = Blueprint('main', __name__)

# 获取日志记录器
logger = logging.getLogger(__name__)

def get_services():
    """获取服务层实例（延迟导入避免循环导入）"""
    try:
        from app.services import SyncService, MonitoringService
        return {
            'sync_service': SyncService(logger=current_app.logger),
            'monitoring_service': MonitoringService(logger=current_app.logger)
        }
    except ImportError:
        return None


@main_bp.route('/')
def dashboard():
    """主仪表板页面"""
    try:
        # 获取基础统计数据用于页面预加载
        services = get_services()
        page_data = {}
        
        if services:
            try:
                # 获取基础统计数据
                stats = services['sync_service'].get_dashboard_stats()
                page_data = {
                    'initial_stats': stats,
                    'page_title': '飞书-Notion同步系统',
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            except Exception as e:
                logger.warning(f"获取页面预载数据失败: {e}")
                page_data = {'page_title': '飞书-Notion同步系统'}
        
        return render_template('sync_management.html', **page_data)
    except Exception as e:
        logger.error(f"渲染主页失败: {e}")
        return render_template('error.html', error_message="页面加载失败"), 500


@main_bp.route('/dashboard')
def old_dashboard():
    """
    ⚠️ 废弃页面 - 向后兼容的仪表板路由 ⚠️
    
    此路由仅用于向后兼容，所有功能应在主页 / 实现
    
    禁止在 /dashboard 页面添加以下功能：
    - ❌ 新建配置功能
    - ❌ 手动同步功能  
    - ❌ 批量同步功能
    - ❌ 配置管理功能
    - ❌ 任何业务逻辑功能
    
    所有功能必须在主页 / 路由实现！
    """
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"渲染废弃仪表板页面失败: {e}")
        return render_template('error.html', error_message="页面加载失败"), 500


@main_bp.route('/about')
def about():
    """关于页面"""
    try:
        return render_template('about.html')
    except Exception as e:
        logger.error(f"渲染关于页面失败: {e}")
        return render_template('error.html', error_message="页面加载失败"), 500


@main_bp.route('/help')
def help_page():
    """帮助页面"""
    try:
        return render_template('help.html')
    except Exception as e:
        logger.error(f"渲染帮助页面失败: {e}")
        return render_template('error.html', error_message="页面加载失败"), 500


# ==================== 页面数据接口 ====================
# 这些接口专门为前端页面提供数据，不包含在API v1中

@main_bp.route('/page-data/navigation')
def get_navigation_data():
    """获取导航数据"""
    try:
        navigation = {
            "main_menu": [
                {"name": "仪表板", "url": "/", "icon": "dashboard"},
                {"name": "同步配置", "url": "/#/configs", "icon": "settings"},
                {"name": "同步记录", "url": "/#/records", "icon": "list"},
                {"name": "批量操作", "url": "/#/batch", "icon": "batch"},
                {"name": "监控统计", "url": "/#/monitoring", "icon": "chart"}
            ],
            "user_menu": [
                {"name": "设置", "url": "/#/settings", "icon": "gear"},
                {"name": "帮助", "url": "/help", "icon": "help"},
                {"name": "关于", "url": "/about", "icon": "info"}
            ]
        }
        return jsonify({"success": True, "data": navigation})
    except Exception as e:
        logger.error(f"获取导航数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route('/page-data/breadcrumb')
def get_breadcrumb_data():
    """获取面包屑导航数据"""
    try:
        # 从请求参数获取当前路径
        current_path = request.args.get('path', '/')
        
        breadcrumbs = []
        if current_path == '/':
            breadcrumbs = [{"name": "仪表板", "url": "/"}]
        elif current_path.startswith('/#/configs'):
            breadcrumbs = [
                {"name": "仪表板", "url": "/"},
                {"name": "同步配置", "url": "/#/configs"}
            ]
        elif current_path.startswith('/#/records'):
            breadcrumbs = [
                {"name": "仪表板", "url": "/"},
                {"name": "同步记录", "url": "/#/records"}
            ]
        elif current_path.startswith('/#/batch'):
            breadcrumbs = [
                {"name": "仪表板", "url": "/"},
                {"name": "批量操作", "url": "/#/batch"}
            ]
        elif current_path.startswith('/#/monitoring'):
            breadcrumbs = [
                {"name": "仪表板", "url": "/"},
                {"name": "监控统计", "url": "/#/monitoring"}
            ]
        else:
            breadcrumbs = [{"name": "仪表板", "url": "/"}]
        
        return jsonify({"success": True, "data": breadcrumbs})
    except Exception as e:
        logger.error(f"获取面包屑数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route('/page-data/system-info')
def get_system_info():
    """获取系统信息（用于页面footer等）"""
    try:
        services = get_services()
        system_info = {
            "app_name": "飞书-Notion同步系统",
            "version": "v1.0.0",
            "build_time": datetime.now().strftime('%Y-%m-%d'),
            "description": "企业级文档同步解决方案",
            "copyright": f"© {datetime.now().year} Sync System. All rights reserved."
        }
        
        # 如果服务可用，添加运行时信息
        if services:
            try:
                settings = services['monitoring_service'].get_system_settings()
                system_info.update({
                    "api_version": settings.get("api_version", "v1"),
                    "system_status": settings.get("system_status", "running")
                })
            except Exception as e:
                logger.warning(f"获取运行时信息失败: {e}")
        
        return jsonify({"success": True, "data": system_info})
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== 错误处理 ====================

@main_bp.errorhandler(404)
def page_not_found(error):
    """404错误处理"""
    return render_template('error.html', 
                         error_code=404,
                         error_message="页面未找到"), 404


@main_bp.errorhandler(500)
def internal_server_error(error):
    """500错误处理"""
    logger.error(f"内部服务器错误: {error}")
    return render_template('error.html',
                         error_code=500, 
                         error_message="内部服务器错误"), 500


@main_bp.errorhandler(403)
def forbidden(error):
    """403错误处理"""
    return render_template('error.html',
                         error_code=403,
                         error_message="访问被禁止"), 403