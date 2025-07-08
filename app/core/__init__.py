"""
Core package - 核心模块

包含应用工厂、任务处理等核心功能
注意：数据库管理已迁移到 database.connection 模块
"""

from .app_factory import create_app
from .task_processor import get_task_processor, start_task_processor, stop_task_processor

__all__ = [
    'create_app',
    'get_task_processor',
    'start_task_processor', 
    'stop_task_processor'
]