#!/usr/bin/env python3
"""
同步服务层 - 基于SQLAlchemy ORM的实现
"""
import os
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import logging

from app.utils.helpers import get_beijing_time

from database.connection import db
from database.models import SyncRecord, SyncConfig, ImageMapping

# 定义项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class SyncService:
    """同步服务类 - 处理同步相关的核心业务逻辑（SQLAlchemy版本）"""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def format_datetime(self, dt: datetime = None) -> str:
        """统一日期时间格式处理"""
        if isinstance(dt, str):
            return dt
        elif isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def model_to_dict(self, model_instance) -> Dict[str, Any]:
        """将SQLAlchemy模型实例转换为字典"""
        if model_instance is None:
            return {}
        
        result = {}
        for column in model_instance.__table__.columns:
            value = getattr(model_instance, column.name)
            if isinstance(value, datetime):
                result[column.name] = self.format_datetime(value)
            else:
                result[column.name] = value
        return result
    
    def generate_record_number(self) -> str:
        """生成唯一记录编号"""
        timestamp = int(time.time())
        random_suffix = random.randint(100, 999)
        return f"{timestamp}_{random_suffix}"
    
    # ==================== 同步配置管理 ====================
    
    def get_sync_configs(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """获取同步配置列表（优化版本）"""
        try:
            per_page = min(per_page, 50)  # 限制最大每页数量
            offset = (page - 1) * per_page
            
            with db.get_session() as session:
                # 使用单个查询获取总数和数据，减少数据库往返
                from sqlalchemy import func
                
                # 获取分页数据和总数（优化：使用窗口函数）
                query = session.query(SyncConfig).order_by(
                    SyncConfig.updated_at.desc()  # 改用updated_at，有索引
                )
                
                # 先获取总数（使用更高效的count查询）
                total = query.with_entities(func.count(SyncConfig.id)).scalar()
                
                # 然后获取分页数据
                configs = query.offset(offset).limit(per_page).all()
                
                config_list = [self.model_to_dict(config) for config in configs]
                
                return {
                    'items': config_list,
                    'pagination': {
                        'page': page,
                        'limit': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    }
                }
        except Exception as e:
            self.logger.error(f"获取同步配置列表失败: {e}")
            raise
    
    def create_sync_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建同步配置"""
        try:
            platform = config_data.get('platform')
            document_id = config_data.get('document_id')
            sync_direction = config_data.get('sync_direction')
            
            # 验证必需字段
            if not all([platform, document_id, sync_direction]):
                raise ValueError("缺少必需字段: platform, document_id, sync_direction")
            
            # 验证平台类型
            if platform not in ['feishu', 'notion']:
                raise ValueError("无效的平台类型")
            
            # 验证同步方向
            if sync_direction not in ['bidirectional', 'feishu_to_notion']:
                raise ValueError("无效的同步方向")
            
            with db.get_session() as session:
                # 检查是否已存在相同配置
                existing = session.query(SyncConfig).filter(
                    SyncConfig.platform == platform,
                    SyncConfig.document_id == document_id
                ).first()
                
                if existing:
                    raise ValueError("该文档的同步配置已存在")
                
                # 创建新配置
                new_config = SyncConfig(
                    platform=platform,
                    document_id=document_id,
                    sync_direction=sync_direction,
                    is_sync_enabled=config_data.get('is_sync_enabled', True),
                    auto_sync=config_data.get('auto_sync', True),
                    webhook_url=config_data.get('webhook_url'),
                    notion_category=config_data.get('notion_category')
                )
                
                session.add(new_config)
                session.commit()
                
                return {"config_id": new_config.id, "message": "同步配置创建成功"}
                
        except Exception as e:
            self.logger.error(f"创建同步配置失败: {e}")
            raise
    
    def update_sync_config(self, config_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新同步配置"""
        try:
            with db.get_session() as session:
                # 检查配置是否存在
                config = session.query(SyncConfig).filter(SyncConfig.id == config_id).first()
                if not config:
                    raise ValueError("配置不存在")
                
                # 更新字段
                updated = False
                for field in ['is_sync_enabled', 'auto_sync', 'webhook_url', 'notion_category']:
                    if field in update_data:
                        setattr(config, field, update_data[field])
                        updated = True
                
                if not updated:
                    raise ValueError("没有提供要更新的字段")
                
                config.updated_at = get_beijing_time().replace(tzinfo=None)
                session.commit()
                
                return {"message": "配置更新成功"}
                
        except Exception as e:
            self.logger.error(f"更新同步配置失败: {e}")
            raise
    
    def get_sync_config_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取单个同步配置"""
        try:
            with db.get_session() as session:
                config = session.query(SyncConfig).filter(SyncConfig.id == config_id).first()
                
                if not config:
                    return None
                
                return self.model_to_dict(config)
        except Exception as e:
            self.logger.error(f"获取同步配置失败: {e}")
            raise
    
    def delete_sync_config(self, config_id: int) -> Dict[str, Any]:
        """删除同步配置"""
        try:
            with db.get_session() as session:
                config = session.query(SyncConfig).filter(SyncConfig.id == config_id).first()
                
                if not config:
                    raise ValueError("配置不存在")
                
                session.delete(config)
                session.commit()
                
                return {"message": "配置已删除"}
        except Exception as e:
            self.logger.error(f"删除同步配置失败: {e}")
            raise
    
    # ==================== 同步记录管理 ====================
    
    def get_sync_records(self, page: int = 1, per_page: int = 20, status: str = None, platform: str = None) -> Dict[str, Any]:
        """获取同步记录列表（优化版本）"""
        try:
            per_page = min(per_page, 100)
            offset = (page - 1) * per_page
            
            with db.get_session() as session:
                from sqlalchemy import func
                
                # 构建基础查询
                query = session.query(SyncRecord)
                
                # 优化过滤条件，利用复合索引
                if status and platform:
                    # 同时有状态和平台过滤，使用复合条件
                    query = query.filter(
                        SyncRecord.sync_status == status,
                        SyncRecord.source_platform == platform
                    )
                elif status:
                    query = query.filter(SyncRecord.sync_status == status)
                elif platform:
                    query = query.filter(SyncRecord.source_platform == platform)
                
                # 获取总数（优化查询）
                total = query.with_entities(func.count(SyncRecord.id)).scalar()
                
                # 获取分页数据，使用索引优化的排序
                records = query.order_by(
                    SyncRecord.created_at.desc()
                ).offset(offset).limit(per_page).all()
                
                records_list = [self.model_to_dict(record) for record in records]
                
                return {
                    'items': records_list,
                    'pagination': {
                        'page': page,
                        'limit': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    }
                }
        except Exception as e:
            self.logger.error(f"获取同步记录列表失败: {e}")
            raise
    
    def create_sync_records_batch(self, document_ids: List[str], force_sync: bool = False) -> Dict[str, Any]:
        """批量创建同步记录"""
        try:
            if not document_ids:
                raise ValueError("请提供要同步的文档ID")
            
            if len(document_ids) > 50:
                raise ValueError("单次最多只能同步50个文档")
            
            created_records = []
            
            with db.get_session() as session:
                for doc_id in document_ids:
                    try:
                        # 检查是否已存在同步记录
                        existing_record = session.query(SyncRecord).filter(
                            SyncRecord.source_platform == 'feishu',
                            SyncRecord.source_id == doc_id
                        ).order_by(SyncRecord.created_at.desc()).first()
                        
                        if existing_record and not force_sync:
                            if existing_record.sync_status in ['pending', 'processing']:
                                created_records.append({
                                    'document_id': doc_id,
                                    'record_id': existing_record.id,
                                    'status': 'exists',
                                    'message': '同步任务已存在，正在处理中'
                                })
                                continue
                            elif existing_record.sync_status == 'success' and existing_record.target_id:
                                # 如果已经成功同步且有target_id，重用现有记录而不是创建新的
                                existing_record.sync_status = 'pending'
                                existing_record.updated_at = get_beijing_time().replace(tzinfo=None)
                                session.flush()
                                
                                created_records.append({
                                    'document_id': doc_id,
                                    'record_id': existing_record.id,
                                    'status': 'reused',
                                    'message': '重用现有同步记录，将更新已同步的Notion页面'
                                })
                                continue
                        
                        # 创建新的同步记录
                        record_number = self.generate_record_number()
                        new_record = SyncRecord(
                            record_number=record_number,
                            source_platform='feishu',
                            target_platform='notion',
                            source_id=doc_id,
                            content_type='document',
                            sync_status='pending'
                        )
                        
                        session.add(new_record)
                        session.flush()  # 获取ID但不提交
                        
                        created_records.append({
                            'document_id': doc_id,
                            'record_id': new_record.id,
                            'record_number': record_number,
                            'status': 'created',
                            'message': '同步任务创建成功'
                        })
                        
                    except Exception as e:
                        created_records.append({
                            'document_id': doc_id,
                            'status': 'error',
                            'message': f'创建失败: {str(e)}'
                        })
                
                session.commit()
            
            # 统计结果
            created_count = len([r for r in created_records if r['status'] == 'created'])
            exists_count = len([r for r in created_records if r['status'] == 'exists'])
            reused_count = len([r for r in created_records if r['status'] == 'reused'])
            error_count = len([r for r in created_records if r['status'] == 'error'])
            
            return {
                'total_requested': len(document_ids),
                'created_count': created_count,
                'exists_count': exists_count,
                'reused_count': reused_count,
                'error_count': error_count,
                'records': created_records
            }
            
        except Exception as e:
            self.logger.error(f"批量创建同步记录失败: {e}")
            raise
    
    def delete_sync_records_batch(self, record_ids: List[int] = None, status: str = None) -> Dict[str, Any]:
        """批量删除同步记录"""
        try:
            if not record_ids and not status:
                raise ValueError("请提供要删除的记录ID或状态")
            
            with db.get_session() as session:
                if record_ids:
                    if len(record_ids) > 100:
                        raise ValueError("单次最多只能删除100条记录")
                    
                    deleted_count = session.query(SyncRecord).filter(
                        SyncRecord.id.in_(record_ids)
                    ).delete(synchronize_session=False)
                
                elif status:
                    if status == 'all':
                        # 删除所有记录
                        deleted_count = session.query(SyncRecord).delete(synchronize_session=False)
                    elif status in ['failed', 'completed', 'pending', 'success', 'processing', 'error']:
                        deleted_count = session.query(SyncRecord).filter(
                            SyncRecord.sync_status == status
                        ).delete(synchronize_session=False)
                    else:
                        raise ValueError("无效的状态值")
                
                session.commit()
                
                return {
                    "message": f"成功删除 {deleted_count} 条记录",
                    "deleted_count": deleted_count
                }
                
        except Exception as e:
            self.logger.error(f"批量删除同步记录失败: {e}")
            raise
    
    def retry_sync_record(self, record_id: int) -> Dict[str, Any]:
        """重试单个同步记录"""
        try:
            with db.get_session() as session:
                # 获取记录
                record = session.query(SyncRecord).filter(SyncRecord.id == record_id).first()
                if not record:
                    raise ValueError(f"记录 {record_id} 不存在")
                
                # 检查记录状态
                if record.sync_status not in ['failed', 'error']:
                    raise ValueError(f"记录 {record_id} 状态为 {record.sync_status}，无需重试")
                
                # 重置记录状态
                record.sync_status = 'pending'
                record.error_message = None
                record.updated_at = get_beijing_time().replace(tzinfo=None)
                session.commit()
                
                self.logger.info(f"已重试同步记录: {record_id}")
                
                return {
                    "message": f"已重试记录 {record_id}",
                    "record_id": record_id,
                    "status": "pending"
                }
                
        except Exception as e:
            self.logger.error(f"重试同步记录失败: {e}")
            raise
    
    def retry_sync_records_batch(self, record_ids: List[int], retry_failed_only: bool = True) -> Dict[str, Any]:
        """批量重试同步记录"""
        try:
            if not record_ids:
                raise ValueError("请提供要重试的记录ID")
            
            if len(record_ids) > 100:
                raise ValueError("单次最多只能重试100条记录")
            
            with db.get_session() as session:
                # 构建查询条件
                query = session.query(SyncRecord).filter(SyncRecord.id.in_(record_ids))
                
                if retry_failed_only:
                    query = query.filter(SyncRecord.sync_status == 'failed')
                
                # 更新记录状态
                updated_count = 0
                for record in query.all():
                    record.sync_status = 'pending'
                    record.error_message = None
                    record.updated_at = get_beijing_time().replace(tzinfo=None)
                    updated_count += 1
                
                session.commit()
                
                return {
                    "message": f"成功提交 {updated_count} 个重试任务",
                    "updated_count": updated_count
                }
                
        except Exception as e:
            self.logger.error(f"批量重试同步记录失败: {e}")
            raise
    
    # ==================== 统计和监控 ====================
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """获取仪表板统计数据（优化版本）"""
        try:
            with db.get_session() as session:
                from sqlalchemy import func, case
                
                # 使用单个查询获取配置统计
                config_stats = session.query(
                    func.count(SyncConfig.id).label('total_configs'),
                    func.sum(case((SyncConfig.is_sync_enabled == True, 1), else_=0)).label('active_configs')
                ).first()
                
                # 使用单个查询获取记录统计
                record_stats = session.query(
                    func.count(SyncRecord.id).label('total_records'),
                    func.sum(case((SyncRecord.sync_status == 'success', 1), else_=0)).label('success_records'),
                    func.sum(case((SyncRecord.sync_status == 'failed', 1), else_=0)).label('failed_records'),
                    func.sum(case((SyncRecord.sync_status == 'pending', 1), else_=0)).label('pending_records')
                ).first()
                
                # 计算成功率
                total_records = record_stats.total_records or 0
                success_records = record_stats.success_records or 0
                success_rate = (success_records / total_records * 100) if total_records > 0 else 0
                
                return {
                    "total_configs": config_stats.total_configs or 0,
                    "active_configs": config_stats.active_configs or 0,
                    "total_records": total_records,
                    "success_records": success_records,
                    "failed_records": record_stats.failed_records or 0,
                    "pending_records": record_stats.pending_records or 0,
                    "success_rate": round(success_rate, 2)
                }
        except Exception as e:
            self.logger.error(f"获取仪表板统计失败: {e}")
            raise
    
    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取同步历史记录"""
        try:
            with db.get_session() as session:
                records = session.query(SyncRecord).order_by(
                    SyncRecord.created_at.desc()
                ).limit(limit).all()
                
                return [self.model_to_dict(record) for record in records]
        except Exception as e:
            self.logger.error(f"获取同步历史失败: {e}")
            raise
    
    def delete_sync_record(self, record_id: int) -> Dict[str, Any]:
        """删除单个同步记录"""
        try:
            with db.get_session() as session:
                # 检查记录是否存在
                record = session.query(SyncRecord).filter(SyncRecord.id == record_id).first()
                if not record:
                    raise ValueError("记录不存在")
                
                session.delete(record)
                session.commit()
                
                return {"message": "记录已删除"}
                
        except Exception as e:
            self.logger.error(f"删除同步记录失败: {e}")
            raise
    
    def get_sync_record_detail(self, record_id: int) -> Dict[str, Any]:
        """获取单个同步记录详情"""
        try:
            with db.get_session() as session:
                record = session.query(SyncRecord).filter(SyncRecord.id == record_id).first()
                
                if not record:
                    raise ValueError("记录不存在")
                
                return self.model_to_dict(record)
                
        except Exception as e:
            self.logger.error(f"获取同步记录详情失败: {e}")
            raise