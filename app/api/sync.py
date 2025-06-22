"""
Sync management API endpoints
"""
from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
from typing import Dict, Any

from app.models import SyncRecordService, SyncConfigService
from app.services import FeishuClient, NotionClient

logger = logging.getLogger(__name__)

sync_bp = Blueprint('sync', __name__)

# Initialize clients
feishu_client = FeishuClient()
notion_client = NotionClient()


@sync_bp.route('/status', methods=['GET'])
def get_sync_status():
    """获取同步状态"""
    try:
        # 获取查询参数
        record_id = request.args.get('id', type=int)
        platform = request.args.get('platform')
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        
        if record_id:
            # 获取特定同步记录
            record = SyncRecordService.get_sync_record(record_id)
            if not record:
                return jsonify({"error": "同步记录不存在"}), 404
            
            return jsonify({
                "record": {
                    "id": record.id,
                    "source_platform": record.source_platform,
                    "target_platform": record.target_platform,
                    "source_id": record.source_id,
                    "target_id": record.target_id,
                    "content_type": record.content_type,
                    "sync_status": record.sync_status,
                    "last_sync_time": record.last_sync_time.isoformat() if record.last_sync_time else None,
                    "error_message": record.error_message,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat()
                }
            })
        
        else:
            # 获取同步历史和统计
            records = SyncRecordService.get_sync_history(platform, status, limit)
            stats = SyncRecordService.get_sync_stats()
            
            record_list = []
            for record in records:
                record_list.append({
                    "id": record.id,
                    "source_platform": record.source_platform,
                    "target_platform": record.target_platform,
                    "source_id": record.source_id,
                    "target_id": record.target_id,
                    "content_type": record.content_type,
                    "sync_status": record.sync_status,
                    "last_sync_time": record.last_sync_time.isoformat() if record.last_sync_time else None,
                    "error_message": record.error_message,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat()
                })
            
            return jsonify({
                "records": record_list,
                "stats": stats,
                "total": len(record_list),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        return jsonify({"error": str(e)}), 500


@sync_bp.route('/history', methods=['GET'])
def get_sync_history():
    """获取同步历史"""
    try:
        platform = request.args.get('platform')
        status = request.args.get('status')
        limit = request.args.get('limit', 100, type=int)
        
        records = SyncRecordService.get_sync_history(platform, status, limit)
        
        history = []
        for record in records:
            history.append({
                "id": record.id,
                "source_platform": record.source_platform,
                "target_platform": record.target_platform,
                "source_id": record.source_id,
                "target_id": record.target_id,
                "content_type": record.content_type,
                "sync_status": record.sync_status,
                "last_sync_time": record.last_sync_time.isoformat() if record.last_sync_time else None,
                "error_message": record.error_message,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat()
            })
        
        return jsonify({
            "history": history,
            "total": len(history),
            "filters": {
                "platform": platform,
                "status": status,
                "limit": limit
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"获取同步历史失败: {e}")
        return jsonify({"error": str(e)}), 500


@sync_bp.route('/trigger', methods=['POST'])
def trigger_sync():
    """手动触发同步"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请提供同步参数"}), 400
        
        source_platform = data.get('source_platform')
        target_platform = data.get('target_platform')
        source_id = data.get('source_id')
        content_type = data.get('content_type', 'document')
        
        if not all([source_platform, target_platform, source_id]):
            return jsonify({"error": "缺少必需参数: source_platform, target_platform, source_id"}), 400
        
        # 检查是否启用同步
        if not SyncConfigService.is_sync_enabled(source_platform, source_id):
            return jsonify({"error": f"文档 {source_id} 未启用同步"}), 400
        
        # 创建同步记录
        try:
            sync_record = SyncRecordService.create_sync_record(
                source_platform=source_platform,
                target_platform=target_platform,
                source_id=source_id,
                content_type=content_type,
                sync_status='pending'
            )
            
            # 在session关闭前提取数据，避免session问题
            try:
                record_id = getattr(sync_record, 'id', None)
                logger.info(f"手动触发同步: {source_platform}->{target_platform}, 记录ID: {record_id}")
            except:
                logger.info(f"手动触发同步: {source_platform}->{target_platform}")
                record_id = None
            
            # 执行实际同步任务
            from app.services.sync_processor import SyncProcessor
            processor = SyncProcessor()
            
            # 异步处理同步任务（在生产环境中应该使用队列）
            try:
                sync_result = processor.process_sync_task(record_id)
                if sync_result.get('success'):
                    logger.info(f"同步任务 {record_id} 执行成功")
                else:
                    logger.warning(f"同步任务 {record_id} 执行失败: {sync_result.get('error')}")
            except Exception as sync_error:
                logger.error(f"同步任务 {record_id} 处理异常: {sync_error}")
                # 不影响API响应，错误信息已记录在数据库中
            
            return jsonify({
                "message": "同步任务已创建",
                "sync_record_id": record_id,
                "status": "pending",
                "source_platform": source_platform,
                "target_platform": target_platform,
                "source_id": source_id,
                "content_type": content_type,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except AttributeError as ae:
            logger.warning(f"同步记录属性访问问题: {ae}")
            return jsonify({
                "message": "同步任务已创建",
                "status": "pending",
                "source_platform": source_platform,
                "target_platform": target_platform,
                "source_id": source_id,
                "content_type": content_type,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    except Exception as e:
        logger.error(f"触发同步失败: {e}")
        return jsonify({"error": str(e)}), 500


@sync_bp.route('/config', methods=['GET', 'POST'])
def sync_config():
    """同步配置管理"""
    if request.method == 'GET':
        try:
            platform = request.args.get('platform')
            enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
            
            if platform:
                configs = SyncConfigService.get_configs_by_platform(platform)
            elif enabled_only:
                configs = SyncConfigService.get_enabled_configs()
            else:
                configs = SyncConfigService.get_all_configs()
            
            config_list = []
            for config in configs:
                config_list.append({
                    "id": config.id,
                    "platform": config.platform,
                    "document_id": config.document_id,
                    "is_sync_enabled": config.is_sync_enabled,
                    "sync_direction": config.sync_direction,
                    "auto_sync": config.auto_sync,
                    "created_at": config.created_at.isoformat(),
                    "updated_at": config.updated_at.isoformat()
                })
            
            stats = SyncConfigService.get_config_stats()
            
            return jsonify({
                "configs": config_list,
                "stats": stats,
                "total": len(config_list),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        except Exception as e:
            logger.error(f"获取同步配置失败: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "请提供配置参数"}), 400
            
            platform = data.get('platform')
            document_id = data.get('document_id')
            sync_direction = data.get('sync_direction')
            is_sync_enabled = data.get('is_sync_enabled', True)
            auto_sync = data.get('auto_sync', True)
            
            if not all([platform, document_id, sync_direction]):
                return jsonify({"error": "缺少必需参数: platform, document_id, sync_direction"}), 400
            
            try:
                # 创建或更新配置
                config = SyncConfigService.create_sync_config(
                    platform=platform,
                    document_id=document_id,
                    sync_direction=sync_direction,
                    is_sync_enabled=is_sync_enabled,
                    auto_sync=auto_sync
                )
                
                logger.info(f"创建/更新同步配置: {platform}:{document_id}")
                
                # 提取基本数据，避免session问题
                try:
                    config_data = {
                        "id": getattr(config, 'id', None),
                        "platform": platform,
                        "document_id": document_id,
                        "is_sync_enabled": is_sync_enabled,
                        "sync_direction": sync_direction,
                        "auto_sync": auto_sync,
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                except:
                    # 如果访问config对象出错，使用传入的参数
                    config_data = {
                        "platform": platform,
                        "document_id": document_id,
                        "is_sync_enabled": is_sync_enabled,
                        "sync_direction": sync_direction,
                        "auto_sync": auto_sync,
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                
                return jsonify({
                    "message": "同步配置已保存",
                    "config": config_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            except AttributeError as ae:
                logger.warning(f"属性访问问题: {ae}")
                return jsonify({
                    "message": "同步配置已保存",
                    "config": {
                        "platform": platform,
                        "document_id": document_id,
                        "sync_direction": sync_direction,
                        "is_sync_enabled": is_sync_enabled,
                        "auto_sync": auto_sync
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        except Exception as e:
            logger.error(f"保存同步配置失败: {e}")
            return jsonify({"error": str(e)}), 500


@sync_bp.route('/config/<int:config_id>', methods=['PUT', 'DELETE'])
def manage_sync_config(config_id):
    """管理特定同步配置"""
    if request.method == 'PUT':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "请提供更新参数"}), 400
            
            success = SyncConfigService.update_sync_config(
                config_id=config_id,
                is_sync_enabled=data.get('is_sync_enabled'),
                sync_direction=data.get('sync_direction'),
                auto_sync=data.get('auto_sync')
            )
            
            if not success:
                return jsonify({"error": "配置不存在"}), 404
            
            logger.info(f"更新同步配置: {config_id}")
            
            return jsonify({
                "message": "配置已更新",
                "config_id": config_id,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        except Exception as e:
            logger.error(f"更新同步配置失败: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            success = SyncConfigService.delete_sync_config(config_id)
            
            if not success:
                return jsonify({"error": "配置不存在"}), 404
            
            logger.info(f"删除同步配置: {config_id}")
            
            return jsonify({
                "message": "配置已删除",
                "config_id": config_id,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        except Exception as e:
            logger.error(f"删除同步配置失败: {e}")
            return jsonify({"error": str(e)}), 500


@sync_bp.route('/pending', methods=['GET'])
def get_pending_syncs():
    """获取待处理的同步任务"""
    try:
        records = SyncRecordService.get_pending_syncs()
        
        pending_list = []
        for record in records:
            pending_list.append({
                "id": record.id,
                "source_platform": record.source_platform,
                "target_platform": record.target_platform,
                "source_id": record.source_id,
                "content_type": record.content_type,
                "created_at": record.created_at.isoformat()
            })
        
        return jsonify({
            "pending_syncs": pending_list,
            "total": len(pending_list),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"获取待处理同步任务失败: {e}")
        return jsonify({"error": str(e)}), 500


@sync_bp.route('/failed', methods=['GET'])
def get_failed_syncs():
    """获取失败的同步任务"""
    try:
        records = SyncRecordService.get_failed_syncs()
        
        failed_list = []
        for record in records:
            failed_list.append({
                "id": record.id,
                "source_platform": record.source_platform,
                "target_platform": record.target_platform,
                "source_id": record.source_id,
                "content_type": record.content_type,
                "error_message": record.error_message,
                "last_sync_time": record.last_sync_time.isoformat() if record.last_sync_time else None,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat()
            })
        
        return jsonify({
            "failed_syncs": failed_list,
            "total": len(failed_list),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"获取失败同步任务失败: {e}")
        return jsonify({"error": str(e)}), 500


@sync_bp.route('/preview', methods=['POST'])
def get_sync_preview():
    """获取同步预览"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请提供预览参数"}), 400
        
        source_platform = data.get('source_platform')
        source_id = data.get('source_id')
        
        if not all([source_platform, source_id]):
            return jsonify({"error": "缺少必需参数: source_platform, source_id"}), 400
        
        from app.services.sync_processor import SyncProcessor
        processor = SyncProcessor()
        
        preview_data = processor.get_sync_preview(source_platform, source_id)
        
        return jsonify({
            "preview": preview_data,
            "source_platform": source_platform,
            "source_id": source_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"获取同步预览失败: {e}")
        return jsonify({"error": str(e)}), 500


@sync_bp.route('/retry/<int:record_id>', methods=['POST'])
def retry_sync(record_id: int):
    """重试同步任务"""
    try:
        # 获取同步记录
        sync_record = SyncRecordService.get_sync_record(record_id)
        if not sync_record:
            return jsonify({"error": "同步记录不存在"}), 404
        
        # 重置状态为pending
        SyncRecordService.update_sync_record(
            record_id,
            sync_status='pending',
            error_message=None
        )
        
        # 执行同步任务
        from app.services.sync_processor import SyncProcessor
        processor = SyncProcessor()
        
        try:
            sync_result = processor.process_sync_task(record_id)
            
            return jsonify({
                "message": "重试同步任务已完成",
                "sync_record_id": record_id,
                "result": sync_result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as sync_error:
            logger.error(f"重试同步任务 {record_id} 失败: {sync_error}")
            return jsonify({
                "message": "重试同步任务失败",
                "sync_record_id": record_id,
                "error": str(sync_error),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    except Exception as e:
        logger.error(f"重试同步任务失败: {e}")
        return jsonify({"error": str(e)}), 500