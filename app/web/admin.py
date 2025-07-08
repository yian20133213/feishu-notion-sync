#!/usr/bin/env python3
"""
管理页面蓝图 - 处理管理员专用页面路由
"""
from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from datetime import datetime
import logging

# 创建管理蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 获取日志记录器
logger = logging.getLogger(__name__)


@admin_bp.route('/')
def admin_dashboard():
    """管理员仪表板"""
    try:
        return render_template('admin/dashboard.html')
    except Exception as e:
        logger.error(f"渲染管理员仪表板失败: {e}")
        return render_template('error.html', error_message="管理页面加载失败"), 500


@admin_bp.route('/system')
def system_management():
    """系统管理页面"""
    try:
        return render_template('admin/system.html')
    except Exception as e:
        logger.error(f"渲染系统管理页面失败: {e}")
        return render_template('error.html', error_message="页面加载失败"), 500


@admin_bp.route('/users')
def user_management():
    """用户管理页面"""
    try:
        return render_template('admin/users.html')
    except Exception as e:
        logger.error(f"渲染用户管理页面失败: {e}")
        return render_template('error.html', error_message="页面加载失败"), 500


@admin_bp.route('/logs')
def log_viewer():
    """日志查看页面"""
    try:
        return render_template('admin/logs.html')
    except Exception as e:
        logger.error(f"渲染日志查看页面失败: {e}")
        return render_template('error.html', error_message="页面加载失败"), 500


@admin_bp.route('/settings')
def system_settings():
    """系统设置页面"""
    try:
        return render_template('admin/settings.html')
    except Exception as e:
        logger.error(f"渲染系统设置页面失败: {e}")
        return render_template('error.html', error_message="页面加载失败"), 500


# ==================== 管理页面数据接口 ====================

@admin_bp.route('/page-data/sidebar')
def get_admin_sidebar():
    """获取管理员侧边栏数据"""
    try:
        sidebar = {
            "sections": [
                {
                    "title": "系统管理",
                    "items": [
                        {"name": "概览", "url": "/admin/", "icon": "dashboard"},
                        {"name": "系统监控", "url": "/admin/system", "icon": "monitor"},
                        {"name": "系统设置", "url": "/admin/settings", "icon": "cog"}
                    ]
                },
                {
                    "title": "用户管理",
                    "items": [
                        {"name": "用户列表", "url": "/admin/users", "icon": "users"},
                        {"name": "权限管理", "url": "/admin/permissions", "icon": "key"}
                    ]
                },
                {
                    "title": "日志分析",
                    "items": [
                        {"name": "系统日志", "url": "/admin/logs", "icon": "file-text"},
                        {"name": "错误报告", "url": "/admin/errors", "icon": "alert-circle"}
                    ]
                }
            ]
        }
        return jsonify({"success": True, "data": sidebar})
    except Exception as e:
        logger.error(f"获取管理员侧边栏数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route('/page-data/stats')
def get_admin_stats():
    """获取管理员统计数据"""
    try:
        # 这里可以调用服务层获取实际统计数据
        stats = {
            "system_uptime": "5天 12小时",
            "total_users": 15,
            "active_sessions": 8,
            "total_syncs_today": 142,
            "error_rate": "0.5%",
            "last_backup": "2小时前"
        }
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        logger.error(f"获取管理员统计数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== 错误处理 ====================

@admin_bp.errorhandler(404)
def admin_page_not_found(error):
    """管理页面404错误处理"""
    return render_template('admin/error.html', 
                         error_code=404,
                         error_message="管理页面未找到"), 404


@admin_bp.errorhandler(500)
def admin_internal_server_error(error):
    """管理页面500错误处理"""
    logger.error(f"管理页面内部服务器错误: {error}")
    return render_template('admin/error.html',
                         error_code=500, 
                         error_message="管理页面内部服务器错误"), 500