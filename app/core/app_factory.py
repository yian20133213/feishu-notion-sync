#!/usr/bin/env python3
"""
Flask应用工厂模式 - 创建和配置Flask应用实例
"""
import os
import signal
import sys
import threading
import queue
import time
import sqlite3
from datetime import datetime
from flask import Flask
from logging.handlers import RotatingFileHandler
import logging

# 定义项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def create_app(config_name='production'):
    """
    应用工厂函数 - 创建Flask应用实例
    
    Args:
        config_name: 配置名称 ('development', 'production', 'testing')
    
    Returns:
        Flask: 配置好的Flask应用实例
    """
    app = Flask(__name__, 
                static_folder='../../static', 
                static_url_path='/static',
                template_folder='../../templates')
    
    # 配置应用
    configure_app(app, config_name)
    
    # 配置日志
    configure_logging(app)
    
    # 初始化数据库
    with app.app_context():
        init_database()
    
    # 注册蓝图
    register_blueprints(app)
    
    # 配置信号处理
    configure_signals(app)
    
    return app


def configure_app(app, config_name):
    """配置应用设置"""
    app.config['DEBUG'] = config_name == 'development'
    app.config['TESTING'] = config_name == 'testing'
    
    # 基础配置
    app.config.update({
        'SECRET_KEY': os.getenv('SECRET_KEY', 'sync_system_secret_key_2024'),
        'DATABASE_URL': os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(PROJECT_ROOT, "feishu_notion_sync.db")}'),
        'API_VERSION': 'v1',
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    })


def configure_logging(app):
    """配置日志系统"""
    if not app.debug and not app.testing:
        # 生产环境日志配置
        log_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s'
        )
        
        # 文件日志处理器
        log_file = os.path.join(PROJECT_ROOT, 'app.log')
        file_handler = RotatingFileHandler(
            log_file, 
            mode='a', 
            maxBytes=5*1024*1024, 
            backupCount=2, 
            encoding=None, 
            delay=False
        )
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('应用日志系统初始化完成')


def register_blueprints(app):
    """注册所有蓝图"""
    try:
        # 注册Web蓝图
        from app.web import main_bp, admin_bp
        app.register_blueprint(main_bp)
        app.register_blueprint(admin_bp)
        
        # 注册API蓝图
        from app.api.v1 import api_v1_bp
        app.register_blueprint(api_v1_bp)
        
        # 始终注册健康检查端点
        register_health_check(app)
        
        app.logger.info('所有蓝图注册完成')
    except ImportError as e:
        app.logger.error(f'蓝图注册失败: {e}')
        # 注册备用蓝图
        register_fallback_blueprints(app)


def register_health_check(app):
    """注册健康检查端点"""
    from flask import jsonify
    
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'version': app.config.get('API_VERSION', 'v1'),
            'timestamp': datetime.now().isoformat()
        })

def register_fallback_blueprints(app):
    """注册备用蓝图（用于向后兼容）"""
    from flask import Blueprint, jsonify
    
    # 创建简单的健康检查蓝图
    health_bp = Blueprint('health', __name__)
    
    @health_bp.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'version': app.config.get('API_VERSION', 'v1'),
            'timestamp': datetime.now().isoformat()
        })
    
    app.register_blueprint(health_bp)


def init_database():
    """初始化数据库连接"""
    from database.connection import db
    
    try:
        # 应用启动时仅测试连接，表的创建和迁移通过 Alembic 命令管理
        if not db.test_connection():
            raise Exception("数据库连接测试失败")
        print("✅ Database connection successful")
        # 注意：在生产环境中，应通过 'alembic upgrade head' 命令管理数据库。
        # 在开发环境中，可以保留下面这行以便快速创建表。
        db.create_tables()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


def configure_signals(app):
    """配置信号处理"""
    def signal_handler(signum, frame):
        """信号处理器"""
        print(f"\n收到信号 {signum}，正在关闭服务...")
        
        # 停止后台任务
        try:
            from app.core.task_processor import get_task_processor
            processor = get_task_processor()
            if processor:
                processor.stop()
        except Exception as e:
            app.logger.error(f"停止任务处理器失败: {e}")
        
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


# 创建图片存储目录
def ensure_directories():
    """确保必要的目录存在"""
    directories = [
        os.path.join(PROJECT_ROOT, 'static', 'images'),
        os.path.join(PROJECT_ROOT, 'logs'),
        os.path.join(PROJECT_ROOT, 'temp')
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# 在模块加载时创建目录
ensure_directories()