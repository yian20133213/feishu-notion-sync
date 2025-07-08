#!/usr/bin/env python3
"""
系统设置相关API路由
"""
import os
from flask import current_app, request
from app.utils import APIResponse
from app.services import FeishuClient, NotionClient, QiniuClient


def register_routes(bp):
    """注册设置相关路由到蓝图"""
    
    @bp.route('/settings/test/feishu', methods=['POST'])
    def test_feishu_connection():
        """测试飞书API连接"""
        try:
            # 从环境变量获取配置
            app_id = os.getenv('FEISHU_APP_ID')
            app_secret = os.getenv('FEISHU_APP_SECRET')
            
            if not app_id or not app_secret:
                return APIResponse.error("飞书API配置不完整", "CONFIG_INCOMPLETE")
            
            # 创建飞书客户端并测试连接
            feishu_client = FeishuClient(current_app.logger)
            
            # 测试获取访问令牌
            access_token = feishu_client.get_access_token()
            if not access_token:
                return APIResponse.error("无法获取访问令牌", "AUTH_FAILED")
            
            # 测试API调用 - 获取用户信息
            test_result = feishu_client.test_connection()
            
            return APIResponse.success({
                "message": "飞书API连接测试成功",
                "details": test_result
            })
            
        except Exception as e:
            return APIResponse.error(f"飞书API连接测试失败: {str(e)}", "CONNECTION_FAILED")
    
    @bp.route('/settings/test/notion', methods=['POST'])
    def test_notion_connection():
        """测试Notion API连接"""
        try:
            # 从环境变量获取配置
            integration_token = os.getenv('NOTION_TOKEN')
            database_id = os.getenv('NOTION_DATABASE_ID')
            
            if not integration_token:
                return APIResponse.error("Notion API配置不完整", "CONFIG_INCOMPLETE")
            
            # 创建Notion客户端并测试连接
            notion_client = NotionClient(integration_token, current_app.logger)
            
            # 测试API调用
            test_result = notion_client.test_connection(database_id)
            
            return APIResponse.success({
                "message": "Notion API连接测试成功",
                "details": test_result
            })
            
        except Exception as e:
            return APIResponse.error(f"Notion API连接测试失败: {str(e)}", "CONNECTION_FAILED")
    
    @bp.route('/settings/test/qiniu', methods=['POST'])
    def test_qiniu_connection():
        """测试七牛云存储连接"""
        try:
            # 从环境变量获取配置
            access_key = os.getenv('QINIU_ACCESS_KEY')
            secret_key = os.getenv('QINIU_SECRET_KEY')
            bucket_name = os.getenv('QINIU_BUCKET')
            cdn_domain = os.getenv('QINIU_CDN_DOMAIN')
            
            if not all([access_key, secret_key, bucket_name]):
                return APIResponse.error("七牛云存储配置不完整", "CONFIG_INCOMPLETE")
            
            # 创建七牛云客户端并测试连接
            qiniu_client = QiniuClient(access_key, secret_key, bucket_name, cdn_domain, current_app.logger)
            
            # 测试连接
            test_result = qiniu_client.test_connection()
            
            return APIResponse.success({
                "message": "七牛云存储连接测试成功",
                "details": test_result
            })
            
        except Exception as e:
            return APIResponse.error(f"七牛云存储连接测试失败: {str(e)}", "CONNECTION_FAILED")
    
    @bp.route('/settings/system/info', methods=['GET'])
    def get_system_info():
        """获取系统信息"""
        try:
            import time
            import psutil
            import platform
            from datetime import datetime, timedelta
            
            # 计算系统运行时间
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            uptime_str = f"{uptime.days}天 {uptime.seconds//3600}小时"
            
            # 获取存储使用情况
            disk_usage = psutil.disk_usage('/')
            storage_used = disk_usage.used / (1024 ** 3)  # GB
            storage_total = disk_usage.total / (1024 ** 3)  # GB
            storage_usage = f"{storage_used:.1f}GB / {storage_total:.1f}GB"
            
            # 检查API连接状态
            api_status_count = 0
            total_apis = 3
            
            # 检查飞书API
            if os.getenv('FEISHU_APP_ID') and os.getenv('FEISHU_APP_SECRET'):
                api_status_count += 1
            
            # 检查Notion API
            if os.getenv('NOTION_INTEGRATION_TOKEN'):
                api_status_count += 1
            
            # 检查七牛云API
            if os.getenv('QINIU_ACCESS_KEY') and os.getenv('QINIU_SECRET_KEY'):
                api_status_count += 1
            
            return APIResponse.success({
                "uptime": uptime_str,
                "storage_usage": storage_usage,
                "api_status": f"{api_status_count}/{total_apis}",
                "version": "v2.4.2",
                "platform": platform.system(),
                "python_version": platform.python_version()
            })
            
        except Exception as e:
            return APIResponse.error(f"获取系统信息失败: {str(e)}", "SYSTEM_INFO_ERROR")
    
    @bp.route('/settings/api/configs', methods=['GET'])
    def get_api_configs():
        """获取API配置信息（只返回非敏感信息）"""
        try:
            configs = {
                "feishu": {
                    "app_id": os.getenv('FEISHU_APP_ID', ''),
                    "webhook_url": "https://sync.yianlu.com/webhook/feishu",
                    "configured": bool(os.getenv('FEISHU_APP_ID') and os.getenv('FEISHU_APP_SECRET'))
                },
                "notion": {
                    "database_id": os.getenv('NOTION_DATABASE_ID', ''),
                    "configured": bool(os.getenv('NOTION_TOKEN'))
                },
                "qiniu": {
                    "access_key": os.getenv('QINIU_ACCESS_KEY', ''),
                    "bucket": os.getenv('QINIU_BUCKET', ''),
                    "cdn_domain": os.getenv('QINIU_CDN_DOMAIN', ''),
                    "configured": bool(os.getenv('QINIU_ACCESS_KEY') and os.getenv('QINIU_SECRET_KEY'))
                }
            }
            
            return APIResponse.success(configs)
            
        except Exception as e:
            return APIResponse.error(f"获取API配置失败: {str(e)}", "CONFIG_ERROR")
    
    @bp.route('/settings/sync/save', methods=['POST'])
    def save_sync_settings():
        """保存同步参数设置"""
        try:
            data = request.get_json()
            if not data:
                return APIResponse.error("请求数据不能为空", "INVALID_REQUEST")
            
            # 验证设置数据
            settings = {
                'sync_timeout': int(data.get('sync_timeout', 60)),
                'retry_count': int(data.get('retry_count', 3)),
                'batch_size': int(data.get('batch_size', 10)),
                'auto_retry': bool(data.get('auto_retry', False)),
                'image_quality': int(data.get('image_quality', 70)),
                'log_retention': int(data.get('log_retention', 30)),
                'enable_webhook': bool(data.get('enable_webhook', True))
            }
            
            # 验证参数范围
            if not (10 <= settings['sync_timeout'] <= 300):
                return APIResponse.error("同步超时时间必须在10-300秒之间", "INVALID_PARAMETER")
            
            if not (1 <= settings['retry_count'] <= 10):
                return APIResponse.error("重试次数必须在1-10次之间", "INVALID_PARAMETER")
            
            if not (1 <= settings['batch_size'] <= 100):
                return APIResponse.error("批量大小必须在1-100之间", "INVALID_PARAMETER")
            
            if not (30 <= settings['image_quality'] <= 100):
                return APIResponse.error("图片质量必须在30-100之间", "INVALID_PARAMETER")
            
            if not (1 <= settings['log_retention'] <= 365):
                return APIResponse.error("日志保留天数必须在1-365天之间", "INVALID_PARAMETER")
            
            # 这里可以将设置保存到数据库或配置文件
            # 暂时记录到日志中
            current_app.logger.info(f"保存同步设置: {settings}")
            
            return APIResponse.success({
                "message": "同步参数设置保存成功",
                "settings": settings
            })
            
        except ValueError as e:
            return APIResponse.error(f"参数格式错误: {str(e)}", "INVALID_PARAMETER")
        except Exception as e:
            return APIResponse.error(f"保存设置失败: {str(e)}", "SAVE_ERROR")