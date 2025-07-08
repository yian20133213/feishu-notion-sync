#!/usr/bin/env python3
"""
同步任务处理器模块 - 处理后台同步任务
"""
import threading
import time
import random
from datetime import datetime
import logging


class SyncTaskProcessor:
    """同步任务处理器"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.check_interval = 30  # 30秒检查一次
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """启动任务处理器"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._process_loop, daemon=True)
            self.thread.start()
            self.logger.info("📋 任务处理循环开始")
            self.logger.info("🚀 同步任务处理器已启动")
    
    def stop(self):
        """停止任务处理器"""
        if self.running:
            self.running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
            self.logger.info("🛑 同步任务处理器已停止")
    
    def _process_loop(self):
        """主处理循环"""
        while self.running:
            try:
                self._process_pending_tasks()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"任务处理循环错误: {e}")
                time.sleep(5)  # 错误时短暂等待
    
    def _process_pending_tasks(self):
        """处理待处理的任务"""
        try:
            from database.connection import db
            from database.models import SyncRecord
            from app.utils.helpers import format_datetime
            
            with db.get_session() as session:
                # 获取待处理的任务
                pending_tasks = session.query(SyncRecord).filter(
                    SyncRecord.sync_status == 'pending'
                ).order_by(SyncRecord.created_at).limit(5).all()
                
                for task in pending_tasks:
                    if not self.running:
                        break
                    
                    try:
                        self.logger.info(f"🔄 开始处理同步任务: {task.record_number}")
                        self._execute_sync_task(task)
                    except Exception as e:
                        self.logger.error(f"❌ 任务 {task.record_number} 处理失败: {e}")
                        # 更新任务状态为失败
                        try:
                            task.sync_status = 'failed'
                            task.error_message = str(e)
                            task.updated_at = format_datetime()
                            session.commit()
                        except Exception as update_error:
                            self.logger.error(f"更新任务状态失败: {update_error}")
                        
        except Exception as e:
            self.logger.error(f"获取待处理任务失败: {e}")
    
    def _execute_sync_task(self, task):
        """执行同步任务"""
        try:
            from database.connection import db
            from database.models import SyncRecord
            from app.utils.helpers import format_datetime
            
            # 更新状态为处理中
            with db.get_session() as session:
                sync_record = session.query(SyncRecord).filter(SyncRecord.id == task.id).first()
                if sync_record:
                    sync_record.sync_status = 'processing'
                    sync_record.updated_at = format_datetime()
                    session.commit()
            
            # 调用真实的同步处理器
            try:
                from app.services.sync_processor import SyncProcessor
                
                sync_processor = SyncProcessor()
                result = sync_processor.process_sync_task(task.id)
                
                if result.get('success'):
                    self.logger.info(f"✅ 任务 {task.record_number} 处理成功")
                else:
                    self.logger.error(f"❌ 任务 {task.record_number} 处理失败: {result.get('error')}")
                    
            except Exception as e:
                self.logger.error(f"❌ 任务 {task.record_number} 同步处理器调用失败: {e}")
                raise
                
        except Exception as e:
            self.logger.error(f"执行同步任务异常: {e}")
            raise
    
    def _generate_target_id(self, task):
        """生成模拟的目标平台ID"""
        try:
            from database.connection import db
            from database.models import SyncRecord
            import uuid
            
            with db.get_session() as session:
                # 获取同步记录详情
                record = session.query(SyncRecord).filter(SyncRecord.id == task.id).first()
                
                if not record:
                    return None
                
                target_platform = record.target_platform
                source_id = record.source_id
                
                # 根据目标平台生成相应格式的ID
                if target_platform == 'notion':
                    # Notion页面ID格式：32位UUID（带破折号）
                    return str(uuid.uuid4())
                elif target_platform == 'feishu':
                    # 飞书文档ID格式
                    return f"doccn{uuid.uuid4().hex[:20]}"
                else:
                    # 默认格式
                    return f"sync_{uuid.uuid4().hex[:16]}"
                    
        except Exception as e:
            self.logger.error(f"生成目标ID失败: {e}")
            return f"generated_{random.randint(1000, 9999)}"
    
    def get_status(self):
        """获取处理器状态"""
        return {
            "running": self.running,
            "thread_alive": self.thread.is_alive() if self.thread else False,
            "check_interval": self.check_interval
        }


# 全局任务处理器实例
_task_processor = None

def get_task_processor():
    """获取任务处理器实例"""
    global _task_processor
    if _task_processor is None:
        _task_processor = SyncTaskProcessor()
    return _task_processor

def start_task_processor():
    """启动任务处理器"""
    processor = get_task_processor()
    processor.start()
    return processor

def stop_task_processor():
    """停止任务处理器"""
    processor = get_task_processor()
    processor.stop()