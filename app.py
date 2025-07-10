#!/usr/bin/env python3
"""
Flask应用启动文件 - 使用应用工厂模式
"""
import os
import sys
from app.core import create_app, start_task_processor

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有python-dotenv包，直接加载.env文件
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value


def main():
    """主函数 - 启动Flask应用"""
    # 获取配置环境
    config_name = os.getenv('FLASK_ENV', 'production')
    
    # 创建应用实例
    app = create_app(config_name)
    
    # 启动同步任务处理器
    sync_processor = start_task_processor()
    
    # 输出启动信息
    print("🚀 启动飞书-Notion同步服务...")
    print("📍 服务地址: http://0.0.0.0:5000")
    print("🌐 Webhook地址: https://sync.yianlu.com/webhook/feishu")
    print("🔍 健康检查: https://sync.yianlu.com/health")
    print("📊 管理面板: https://sync.yianlu.com/")
    print("⚡ 同步任务处理器: 已启动 (每30秒检查待处理任务)")
    
    try:
        # 启动Flask应用
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False
        )
    finally:
        # 确保优雅关闭
        if sync_processor:
            sync_processor.stop()


if __name__ == '__main__':
    main()