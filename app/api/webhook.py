"""
Webhook endpoints for receiving external events
"""
from flask import Blueprint, request, jsonify
import json
import logging
from datetime import datetime

from app.services import FeishuClient
from app.models import SyncRecordService, SyncConfigService

logger = logging.getLogger(__name__)

webhook_bp = Blueprint('webhook', __name__)

# Initialize Feishu client
feishu_client = FeishuClient()


@webhook_bp.route('/feishu', methods=['POST'])
def feishu_webhook():
    """处理飞书Webhook请求"""
    try:
        # 获取请求头信息
        timestamp = request.headers.get('X-Lark-Request-Timestamp', '')
        nonce = request.headers.get('X-Lark-Request-Nonce', '')
        signature = request.headers.get('X-Lark-Signature', '')
        
        # 获取请求体
        body = request.get_data(as_text=True)
        
        logger.info(f"收到飞书Webhook请求:")
        logger.info(f"Timestamp: {timestamp}")
        logger.info(f"Nonce: {nonce}")
        logger.info(f"Signature: {signature}")
        logger.debug(f"Body: {body}")
        
        # 解析JSON数据
        try:
            data = request.get_json()
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}")
            return jsonify({"error": "Invalid JSON"}), 400
        
        if not data:
            logger.error("Empty request body")
            return jsonify({"error": "Empty request body"}), 400
        
        # 处理URL验证挑战
        if 'challenge' in data:
            logger.info("收到URL验证挑战，返回challenge")
            return jsonify({
                "challenge": data['challenge']
            })
        
        # 验证签名（生产环境启用）
        if not request.args.get('skip_verification'):
            if not feishu_client.verify_webhook_signature(timestamp, nonce, body, signature):
                logger.warning("飞书Webhook签名验证失败")
                return jsonify({"error": "Invalid signature"}), 401
        
        # 处理不同类型的事件
        header = data.get('header', {})
        event_type = header.get('event_type', '')
        event_id = header.get('event_id', '')
        
        logger.info(f"处理事件: {event_type} (ID: {event_id})")
        
        # 处理消息事件
        if event_type == 'im.message.receive_v1':
            return _handle_message_event(data)
        
        # 处理文档事件
        elif event_type.startswith('drive.file'):
            return _handle_document_event(data, event_type)
        
        # 处理多维表格事件
        elif event_type.startswith('bitable'):
            return _handle_bitable_event(data, event_type)
        
        else:
            logger.info(f"未处理的事件类型: {event_type}")
            return jsonify({"code": 0, "msg": "event ignored"})
        
    except Exception as e:
        logger.error(f"处理Webhook请求出错: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def _handle_message_event(data):
    """处理消息事件"""
    try:
        event = data.get('event', {})
        message = event.get('message', {})
        sender = event.get('sender', {})
        
        message_type = message.get('message_type', '')
        content = message.get('content', '')
        
        logger.info(f"收到消息: 类型={message_type}, 发送者={sender.get('sender_id', {}).get('user_id', 'unknown')}")
        
        # 这里可以添加消息处理逻辑，比如命令解析等
        # 目前只记录日志
        
        return jsonify({"code": 0, "msg": "message processed"})
    
    except Exception as e:
        logger.error(f"处理消息事件失败: {e}")
        return jsonify({"error": str(e)}), 500


def _handle_document_event(data, event_type):
    """处理文档事件"""
    try:
        event = data.get('event', {})
        file_token = event.get('file_token', '')
        file_type = event.get('file_type', '')
        
        logger.info(f"文档事件: {event_type}, 文件={file_token}, 类型={file_type}")
        
        # 检查是否启用同步
        if not SyncConfigService.is_auto_sync_enabled('feishu', file_token):
            logger.info(f"文档 {file_token} 未启用自动同步")
            return jsonify({"code": 0, "msg": "sync disabled"})
        
        # 创建同步记录
        if event_type in ['drive.file.edit_v1', 'drive.file.title_updated_v1']:
            sync_record = SyncRecordService.create_sync_record(
                source_platform='feishu',
                target_platform='notion',
                source_id=file_token,
                content_type='document',
                sync_status='pending'
            )
            
            logger.info(f"创建同步记录: {sync_record.id}")
            
            # TODO: 这里应该触发异步同步任务
            # 目前只是创建记录，实际同步逻辑在后续阶段实现
            
        elif event_type == 'drive.file.trashed_v1':
            # 文档被删除，标记为删除状态
            logger.info(f"文档 {file_token} 被删除")
            # TODO: 处理删除逻辑
        
        return jsonify({"code": 0, "msg": "document event processed"})
    
    except Exception as e:
        logger.error(f"处理文档事件失败: {e}")
        return jsonify({"error": str(e)}), 500


def _handle_bitable_event(data, event_type):
    """处理多维表格事件"""
    try:
        event = data.get('event', {})
        app_token = event.get('app_token', '')
        table_id = event.get('table_id', '')
        
        logger.info(f"多维表格事件: {event_type}, 应用={app_token}, 表格={table_id}")
        
        # 检查是否启用同步
        if not SyncConfigService.is_auto_sync_enabled('feishu', app_token):
            logger.info(f"多维表格 {app_token} 未启用自动同步")
            return jsonify({"code": 0, "msg": "sync disabled"})
        
        # 创建同步记录
        sync_record = SyncRecordService.create_sync_record(
            source_platform='feishu',
            target_platform='notion',
            source_id=app_token,
            content_type='database',
            sync_status='pending'
        )
        
        logger.info(f"创建多维表格同步记录: {sync_record.id}")
        
        # TODO: 触发多维表格同步任务
        
        return jsonify({"code": 0, "msg": "bitable event processed"})
    
    except Exception as e:
        logger.error(f"处理多维表格事件失败: {e}")
        return jsonify({"error": str(e)}), 500


@webhook_bp.route('/test', methods=['GET', 'POST'])
def webhook_test():
    """Webhook测试接口"""
    if request.method == 'GET':
        return jsonify({
            "message": "Webhook测试接口",
            "endpoints": {
                "feishu": "/webhook/feishu",
                "test": "/webhook/test"
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        logger.info(f"收到测试Webhook请求: {data}")
        
        return jsonify({
            "message": "测试请求已接收",
            "received_data": data,
            "timestamp": datetime.utcnow().isoformat()
        })