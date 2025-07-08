#!/usr/bin/env python3
"""
API v1 主蓝图 - 整合所有API v1路由
"""
from flask import Blueprint

# 创建API v1蓝图
api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# 导入并注册所有子路由
from . import sync_routes
from . import monitoring_routes
from . import config_routes
from . import settings_routes

# 注册子路由到主蓝图
sync_routes.register_routes(api_v1_bp)
monitoring_routes.register_routes(api_v1_bp)
config_routes.register_routes(api_v1_bp)
settings_routes.register_routes(api_v1_bp)