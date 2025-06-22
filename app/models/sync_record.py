"""
Sync record CRUD operations
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from database.models import SyncRecord
from database.connection import get_db_session
import logging

logger = logging.getLogger(__name__)


class SyncRecordService:
    """同步记录服务"""
    
    @staticmethod
    def create_sync_record(
        source_platform: str,
        target_platform: str,
        source_id: str,
        content_type: str,
        target_id: Optional[str] = None,
        sync_status: str = "pending"
    ) -> SyncRecord:
        """创建同步记录"""
        from database.connection import db
        with db.get_session() as session:
            sync_record = SyncRecord(
                source_platform=source_platform,
                target_platform=target_platform,
                source_id=source_id,
                target_id=target_id,
                content_type=content_type,
                sync_status=sync_status
            )
            
            session.add(sync_record)
            session.flush()
            session.refresh(sync_record)
            
            # 在session关闭前提取数据
            record_data = {
                'id': sync_record.id,
                'source_platform': sync_record.source_platform,
                'target_platform': sync_record.target_platform,
                'source_id': sync_record.source_id,
                'target_id': sync_record.target_id,
                'content_type': sync_record.content_type,
                'sync_status': sync_record.sync_status,
                'created_at': sync_record.created_at,
                'updated_at': sync_record.updated_at
            }
            
            logger.info(f"Created sync record: {source_platform}->{target_platform}, ID: {sync_record.id}")
            
            # 创建一个新的对象返回，避免session问题
            from database.models import SyncRecord as SyncRecordModel
            result = SyncRecordModel()
            for key, value in record_data.items():
                setattr(result, key, value)
            
            return result
    
    @staticmethod
    def get_sync_record(record_id: int) -> Optional[SyncRecord]:
        """获取同步记录"""
        from database.connection import db
        with db.get_session() as session:
            record = session.query(SyncRecord).filter(SyncRecord.id == record_id).first()
            return record
    
    @staticmethod
    def get_sync_record_by_source(source_platform: str, source_id: str) -> Optional[SyncRecord]:
        """根据源平台和源ID获取同步记录"""
        with next(get_db_session()) as db:
            record = db.query(SyncRecord).filter(
                and_(
                    SyncRecord.source_platform == source_platform,
                    SyncRecord.source_id == source_id
                )
            ).first()
            return record
    
    @staticmethod
    def update_sync_status(
        record_id: int,
        status: str,
        target_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """更新同步状态"""
        with next(get_db_session()) as db:
            record = db.query(SyncRecord).filter(SyncRecord.id == record_id).first()
            if not record:
                logger.error(f"Sync record {record_id} not found")
                return False
            
            record.sync_status = status
            record.last_sync_time = datetime.utcnow()
            
            if target_id:
                record.target_id = target_id
            
            if error_message:
                record.error_message = error_message
            
            logger.info(f"Updated sync record {record_id} status to {status}")
            return True
    
    @staticmethod
    def get_sync_history(
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[SyncRecord]:
        """获取同步历史"""
        with next(get_db_session()) as db:
            query = db.query(SyncRecord)
            
            if platform:
                query = query.filter(
                    (SyncRecord.source_platform == platform) |
                    (SyncRecord.target_platform == platform)
                )
            
            if status:
                query = query.filter(SyncRecord.sync_status == status)
            
            records = query.order_by(desc(SyncRecord.created_at)).limit(limit).all()
            logger.info(f"Retrieved {len(records)} sync records")
            return records
    
    @staticmethod
    def get_pending_syncs() -> List[SyncRecord]:
        """获取待处理的同步记录"""
        with next(get_db_session()) as db:
            records = db.query(SyncRecord).filter(
                SyncRecord.sync_status == "pending"
            ).order_by(SyncRecord.created_at).all()
            
            logger.info(f"Found {len(records)} pending sync records")
            return records
    
    @staticmethod
    def get_failed_syncs() -> List[SyncRecord]:
        """获取失败的同步记录"""
        with next(get_db_session()) as db:
            records = db.query(SyncRecord).filter(
                SyncRecord.sync_status == "failed"
            ).order_by(desc(SyncRecord.updated_at)).all()
            
            logger.info(f"Found {len(records)} failed sync records")
            return records
    
    @staticmethod
    def delete_sync_record(record_id: int) -> bool:
        """删除同步记录"""
        with next(get_db_session()) as db:
            record = db.query(SyncRecord).filter(SyncRecord.id == record_id).first()
            if not record:
                logger.error(f"Sync record {record_id} not found")
                return False
            
            db.delete(record)
            logger.info(f"Deleted sync record {record_id}")
            return True
    
    @staticmethod
    def update_sync_record(
        record_id: int,
        sync_status: Optional[str] = None,
        target_id: Optional[str] = None,
        error_message: Optional[str] = None,
        last_sync_time: Optional[datetime] = None
    ) -> bool:
        """更新同步记录（兼容方法）"""
        from database.connection import db
        with db.get_session() as session:
            record = session.query(SyncRecord).filter(SyncRecord.id == record_id).first()
            if not record:
                logger.error(f"Sync record {record_id} not found")
                return False
            
            if sync_status:
                record.sync_status = sync_status
                
            if target_id:
                record.target_id = target_id
                
            if error_message:
                record.error_message = error_message
                
            if last_sync_time:
                record.last_sync_time = last_sync_time
            elif sync_status:  # 如果更新状态，自动更新时间
                record.last_sync_time = datetime.utcnow()
            
            record.updated_at = datetime.utcnow()
            
            logger.info(f"Updated sync record {record_id}")
            return True
    
    @staticmethod
    def get_sync_stats() -> Dict[str, Any]:
        """获取同步统计信息"""
        with next(get_db_session()) as db:
            total = db.query(SyncRecord).count()
            success = db.query(SyncRecord).filter(SyncRecord.sync_status == "success").count()
            failed = db.query(SyncRecord).filter(SyncRecord.sync_status == "failed").count()
            pending = db.query(SyncRecord).filter(SyncRecord.sync_status == "pending").count()
            processing = db.query(SyncRecord).filter(SyncRecord.sync_status == "processing").count()
            
            stats = {
                "total": total,
                "success": success,
                "failed": failed,
                "pending": pending,
                "processing": processing,
                "success_rate": (success / total * 100) if total > 0 else 0
            }
            
            logger.info(f"Sync stats: {stats}")
            return stats