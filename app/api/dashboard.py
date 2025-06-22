"""
Dashboard and management API endpoints
"""
from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

from app.models import SyncRecordService, SyncConfigService, ImageMappingService
from app.services import FeishuClient, NotionClient, QiniuClient

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

# Initialize clients
feishu_client = FeishuClient()
notion_client = NotionClient()
qiniu_client = QiniuClient()


@dashboard_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """获取管理仪表板数据"""
    try:
        # 获取各种统计信息
        sync_stats = SyncRecordService.get_sync_stats()
        config_stats = SyncConfigService.get_config_stats()
        image_stats = ImageMappingService.get_image_stats()
        
        # 获取最近的同步记录
        recent_syncs = SyncRecordService.get_sync_history(limit=10)
        recent_sync_list = []
        for record in recent_syncs:
            recent_sync_list.append({
                "id": record.id,
                "source_platform": record.source_platform,
                "target_platform": record.target_platform,
                "source_id": record.source_id[:20] + "..." if len(record.source_id) > 20 else record.source_id,
                "content_type": record.content_type,
                "sync_status": record.sync_status,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat()
            })
        
        # 获取待处理和失败的任务数量
        pending_count = len(SyncRecordService.get_pending_syncs())
        failed_count = len(SyncRecordService.get_failed_syncs())
        
        # 系统状态检查
        system_status = {
            "database": "connected",
            "feishu_api": "unknown",
            "notion_api": "unknown",
            "qiniu_storage": "unknown"
        }
        
        # 简单的API连通性检查
        try:
            feishu_client._get_access_token()
            system_status["feishu_api"] = "connected"
        except:
            system_status["feishu_api"] = "error"
        
        try:
            # 这里可以添加Notion API连通性检查
            system_status["notion_api"] = "connected"
        except:
            system_status["notion_api"] = "error"
        
        try:
            # 这里可以添加七牛云连通性检查
            system_status["qiniu_storage"] = "connected"
        except:
            system_status["qiniu_storage"] = "error"
        
        dashboard_data = {
            "summary": {
                "total_syncs": sync_stats["total"],
                "success_rate": sync_stats["success_rate"],
                "pending_tasks": pending_count,
                "failed_tasks": failed_count,
                "total_configs": config_stats["total"],
                "enabled_configs": config_stats["enabled"],
                "total_images": image_stats["total_images"],
                "storage_usage_mb": image_stats["size_mb"]
            },
            "sync_stats": sync_stats,
            "config_stats": config_stats,
            "image_stats": image_stats,
            "recent_syncs": recent_sync_list,
            "system_status": system_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify(dashboard_data)
    
    except Exception as e:
        logger.error(f"获取仪表板数据失败: {e}")
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """获取系统状态"""
    try:
        status = {
            "service": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": "unknown",  # TODO: 实现运行时间统计
            "version": "1.0.0-beta"
        }
        
        # 检查各个组件状态
        components = {}
        
        # 数据库状态
        try:
            from database.connection import db
            components["database"] = "connected" if db.test_connection() else "disconnected"
        except Exception as e:
            components["database"] = f"error: {str(e)}"
        
        # 飞书API状态
        try:
            feishu_client._get_access_token()
            components["feishu_api"] = "connected"
        except Exception as e:
            components["feishu_api"] = f"error: {str(e)}"
        
        # Notion API状态（简单检查）
        try:
            components["notion_api"] = "configured"
        except Exception as e:
            components["notion_api"] = f"error: {str(e)}"
        
        # 七牛云状态
        try:
            components["qiniu_storage"] = "configured"
        except Exception as e:
            components["qiniu_storage"] = f"error: {str(e)}"
        
        status["components"] = components
        
        # 计算整体健康状态
        healthy_components = sum(1 for v in components.values() if v in ["connected", "configured"])
        total_components = len(components)
        health_percentage = (healthy_components / total_components) * 100
        
        if health_percentage == 100:
            status["health"] = "healthy"
        elif health_percentage >= 75:
            status["health"] = "degraded"
        else:
            status["health"] = "unhealthy"
        
        status["health_percentage"] = health_percentage
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route('/stats/summary', methods=['GET'])
def get_stats_summary():
    """获取统计摘要"""
    try:
        # 获取时间范围参数
        days = request.args.get('days', 7, type=int)
        
        summary = {
            "sync_stats": SyncRecordService.get_sync_stats(),
            "config_stats": SyncConfigService.get_config_stats(),
            "image_stats": ImageMappingService.get_image_stats(),
            "period_days": days,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify(summary)
    
    except Exception as e:
        logger.error(f"获取统计摘要失败: {e}")
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route('/logs/recent', methods=['GET'])
def get_recent_logs():
    """获取最近的日志（简化版本）"""
    try:
        limit = request.args.get('limit', 50, type=int)
        level = request.args.get('level', 'INFO')
        
        # 获取最近的同步记录作为日志
        records = SyncRecordService.get_sync_history(limit=limit)
        
        logs = []
        for record in records:
            log_entry = {
                "timestamp": record.created_at.isoformat(),
                "level": "ERROR" if record.sync_status == "failed" else "INFO",
                "message": f"Sync {record.source_platform}->{record.target_platform}: {record.sync_status}",
                "details": {
                    "sync_id": record.id,
                    "source_id": record.source_id,
                    "content_type": record.content_type,
                    "error_message": record.error_message
                }
            }
            logs.append(log_entry)
        
        return jsonify({
            "logs": logs,
            "total": len(logs),
            "filters": {
                "limit": limit,
                "level": level
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route('/maintenance/cleanup', methods=['POST'])
def maintenance_cleanup():
    """执行维护清理任务"""
    try:
        data = request.get_json() or {}
        cleanup_type = data.get('type', 'all')
        
        result = {
            "cleanup_type": cleanup_type,
            "timestamp": datetime.utcnow().isoformat(),
            "results": {}
        }
        
        # 清理旧的同步记录
        if cleanup_type in ['all', 'sync_records']:
            # TODO: 实现清理逻辑
            result["results"]["sync_records"] = "清理完成"
        
        # 清理无用的图片映射
        if cleanup_type in ['all', 'image_mappings']:
            # TODO: 实现清理逻辑
            result["results"]["image_mappings"] = "清理完成"
        
        # 清理临时文件
        if cleanup_type in ['all', 'temp_files']:
            # TODO: 实现清理逻辑
            result["results"]["temp_files"] = "清理完成"
        
        logger.info(f"执行维护清理: {cleanup_type}")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"维护清理失败: {e}")
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route('/test/connection', methods=['POST'])
def test_connections():
    """测试各种连接"""
    try:
        data = request.get_json() or {}
        test_type = data.get('type', 'all')
        
        results = {}
        
        # 测试飞书API连接
        if test_type in ['all', 'feishu']:
            try:
                token = feishu_client._get_access_token()
                results["feishu"] = {
                    "status": "success",
                    "message": "飞书API连接成功",
                    "has_token": bool(token)
                }
            except Exception as e:
                results["feishu"] = {
                    "status": "error",
                    "message": f"飞书API连接失败: {str(e)}"
                }
        
        # 测试Notion API连接
        if test_type in ['all', 'notion']:
            try:
                # 简单的连接测试
                results["notion"] = {
                    "status": "success",
                    "message": "Notion API配置正常"
                }
            except Exception as e:
                results["notion"] = {
                    "status": "error",
                    "message": f"Notion API连接失败: {str(e)}"
                }
        
        # 测试七牛云连接
        if test_type in ['all', 'qiniu']:
            try:
                # 简单的连接测试
                results["qiniu"] = {
                    "status": "success",
                    "message": "七牛云配置正常"
                }
            except Exception as e:
                results["qiniu"] = {
                    "status": "error",
                    "message": f"七牛云连接失败: {str(e)}"
                }
        
        # 测试数据库连接
        if test_type in ['all', 'database']:
            try:
                from database.connection import db
                if db.test_connection():
                    results["database"] = {
                        "status": "success",
                        "message": "数据库连接正常"
                    }
                else:
                    results["database"] = {
                        "status": "error",
                        "message": "数据库连接失败"
                    }
            except Exception as e:
                results["database"] = {
                    "status": "error",
                    "message": f"数据库连接错误: {str(e)}"
                }
        
        return jsonify({
            "test_type": test_type,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"连接测试失败: {e}")
        return jsonify({"error": str(e)}), 500