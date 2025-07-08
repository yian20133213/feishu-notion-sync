#!/usr/bin/env python3
"""
监控服务层 - 处理系统监控、日志分析和图片统计相关的业务逻辑
"""
import logging
from typing import List, Dict, Any, Optional
from .sync_service import SyncService


class MonitoringService(SyncService):
    """监控服务类 - 继承同步服务的基础功能，专门处理监控和统计相关操作"""
    
    def __init__(self, logger: logging.Logger = None):
        super().__init__(logger)
    
    def get_system_settings(self) -> Dict[str, Any]:
        """获取系统设置"""
        try:
            # 返回一些基本的系统设置信息
            settings = {
                "auto_sync_interval": 30,
                "max_retry_count": 3,
                "webhook_timeout": 30,
                "api_version": "v1",
                "system_status": "running"
            }
            
            return settings
        except Exception as e:
            self.logger.error(f"获取系统设置失败: {e}")
            raise
    
    def get_logs_analysis(self) -> Dict[str, Any]:
        """获取日志分析数据"""
        try:
            from database.connection import db
            from database.models import SyncRecord
            from sqlalchemy import func, and_
            from datetime import datetime, timedelta
            
            with db.get_session() as session:
                # 获取最近的错误日志统计
                yesterday = datetime.now() - timedelta(days=1)
                error_stats = session.query(
                    SyncRecord.sync_status,
                    func.count(SyncRecord.id).label('count')
                ).filter(
                    SyncRecord.created_at > yesterday
                ).group_by(SyncRecord.sync_status).all()
                
                # 获取最近的错误消息
                recent_errors = session.query(
                    SyncRecord.error_message,
                    func.count(SyncRecord.id).label('count')
                ).filter(
                    and_(
                        SyncRecord.sync_status == 'failed',
                        SyncRecord.error_message.isnot(None),
                        SyncRecord.created_at > yesterday
                    )
                ).group_by(SyncRecord.error_message).order_by(
                    func.count(SyncRecord.id).desc()
                ).limit(10).all()
                
                # 转换为字典格式
                error_stats_dict = [
                    {"sync_status": row.sync_status, "count": row.count} 
                    for row in error_stats
                ]
                recent_errors_dict = [
                    {"error_message": row.error_message, "count": row.count} 
                    for row in recent_errors
                ]
                
                return {
                    "error_stats": error_stats_dict,
                    "recent_errors": recent_errors_dict
                }
        except Exception as e:
            self.logger.error(f"获取日志分析失败: {e}")
            raise
    
    def get_images_stats(self) -> Dict[str, Any]:
        """获取图片统计信息"""
        try:
            from database.connection import db
            from database.models import ImageMapping
            from sqlalchemy import func
            
            with db.get_session() as session:
                # 获取总数和总大小
                total_images = session.query(ImageMapping).count()
                total_size = session.query(func.coalesce(func.sum(ImageMapping.size), 0)).scalar() or 0
                
                # 按类型统计
                type_stats = session.query(
                    ImageMapping.mime_type,
                    func.count(ImageMapping.id).label('count'),
                    func.coalesce(func.sum(ImageMapping.size), 0).label('total_size')
                ).group_by(ImageMapping.mime_type).order_by(
                    func.count(ImageMapping.id).desc()
                ).all()
                
                # 转换为字典格式
                type_stats_dict = [
                    {
                        "mime_type": row.mime_type, 
                        "count": row.count, 
                        "total_size": row.total_size
                    } 
                    for row in type_stats
                ]
                
                return {
                    "total_images": total_images,
                    "total_size": total_size,
                    "type_stats": type_stats_dict
                }
        except Exception as e:
            self.logger.error(f"获取图片统计失败: {e}")
            raise
    
    def get_processor_status(self, sync_task_processor) -> Dict[str, Any]:
        """获取同步任务处理器状态"""
        try:
            if not sync_task_processor:
                raise ValueError("任务处理器未初始化")
            
            status = sync_task_processor.get_status()
            
            # 获取待处理任务数量
            try:
                from database.connection import db
                from database.models import SyncRecord
                
                with db.get_session() as session:
                    pending_count = session.query(SyncRecord).filter(
                        SyncRecord.sync_status == 'pending'
                    ).count()
                    
                    processing_count = session.query(SyncRecord).filter(
                        SyncRecord.sync_status == 'processing'
                    ).count()
                    
                    status.update({
                        "pending_tasks": pending_count,
                        "processing_tasks": processing_count
                    })
            except Exception as e:
                self.logger.error(f"获取任务统计失败: {e}")
                status.update({
                    "pending_tasks": 0,
                    "processing_tasks": 0,
                    "error": str(e)
                })
            
            return status
        except Exception as e:
            self.logger.error(f"获取处理器状态失败: {e}")
            raise
    
    def get_system_health(self) -> Dict[str, Any]:
        """系统健康检查"""
        try:
            from database.connection import db
            with db.get_session() as session:
                # 测试数据库连接
                session.execute('SELECT 1').fetchone()
                
                return {
                    'status': 'healthy',
                    'database': 'connected',
                    'version': 'v1',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            raise
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误统计信息"""
        try:
            from database.connection import db
            from database.models import SyncRecord
            from sqlalchemy import func, case, and_
            from datetime import datetime, timedelta
            
            with db.get_session() as session:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                
                # 按时间段统计错误
                error_by_hour = session.query(
                    func.strftime('%H', SyncRecord.created_at).label('hour'),
                    func.count(SyncRecord.id).label('error_count')
                ).filter(
                    and_(
                        SyncRecord.sync_status == 'failed',
                        SyncRecord.created_at > cutoff_time
                    )
                ).group_by(
                    func.strftime('%H', SyncRecord.created_at)
                ).order_by('hour').all()
                
                # 按错误类型统计
                error_type_case = case(
                    (SyncRecord.error_message.like('%timeout%'), 'timeout'),
                    ((SyncRecord.error_message.like('%auth%')) | (SyncRecord.error_message.like('%401%')), 'authentication'),
                    ((SyncRecord.error_message.like('%permission%')) | (SyncRecord.error_message.like('%403%')), 'permission'),
                    ((SyncRecord.error_message.like('%network%')) | (SyncRecord.error_message.like('%connection%')), 'network'),
                    else_='other'
                ).label('error_type')
                
                error_by_type = session.query(
                    error_type_case,
                    func.count(SyncRecord.id).label('count')
                ).filter(
                    and_(
                        SyncRecord.sync_status == 'failed',
                        SyncRecord.error_message.isnot(None),
                        SyncRecord.created_at > cutoff_time
                    )
                ).group_by(error_type_case).order_by(func.count(SyncRecord.id).desc()).all()
                
                return {
                    "timeframe_hours": hours,
                    "error_by_hour": [{'hour': row.hour, 'error_count': row.error_count} for row in error_by_hour],
                    "error_by_type": [{'error_type': row.error_type, 'count': row.count} for row in error_by_type]
                }
        except Exception as e:
            self.logger.error(f"获取错误统计失败: {e}")
            raise
    
    def get_performance_trends(self, days: int = 7) -> Dict[str, Any]:
        """获取性能趋势数据"""
        try:
            from database.connection import db
            from database.models import SyncRecord
            from sqlalchemy import func, case, and_
            from datetime import datetime, timedelta
            
            with db.get_session() as session:
                cutoff_time = datetime.now() - timedelta(days=days)
                
                # 按天统计同步数量
                daily_syncs = session.query(
                    func.date(SyncRecord.created_at).label('sync_date'),
                    func.count(SyncRecord.id).label('total_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'success', 1), else_=0)).label('successful_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'failed', 1), else_=0)).label('failed_syncs')
                ).filter(
                    SyncRecord.created_at > cutoff_time
                ).group_by(
                    func.date(SyncRecord.created_at)
                ).order_by('sync_date').all()
                
                # 计算平均处理时间（使用updated_at - created_at的差值）
                avg_result = session.query(
                    func.avg(
                        func.julianday(SyncRecord.updated_at) - func.julianday(SyncRecord.created_at)
                    ).label('avg_days')
                ).filter(
                    and_(
                        SyncRecord.sync_status.in_(['success', 'failed']),
                        SyncRecord.created_at > cutoff_time
                    )
                ).first()
                
                avg_minutes = round((avg_result.avg_days or 0) * 24 * 60, 2)
                
                return {
                    "timeframe_days": days,
                    "daily_syncs": [
                        {
                            'sync_date': str(row.sync_date), 
                            'total_syncs': row.total_syncs,
                            'successful_syncs': row.successful_syncs,
                            'failed_syncs': row.failed_syncs
                        } for row in daily_syncs
                    ],
                    "avg_processing_time_minutes": avg_minutes
                }
        except Exception as e:
            self.logger.error(f"获取性能趋势失败: {e}")
            raise
    
    def get_platform_statistics(self) -> Dict[str, Any]:
        """获取平台使用统计"""
        try:
            from database.connection import db
            from database.models import SyncRecord
            from sqlalchemy import func, case
            
            with db.get_session() as session:
                # 按源平台统计
                source_platform_stats = session.query(
                    SyncRecord.source_platform,
                    func.count(SyncRecord.id).label('total_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'success', 1), else_=0)).label('successful_syncs'),
                    func.round(
                        (func.sum(case((SyncRecord.sync_status == 'success', 1), else_=0)) * 100.0 / func.count(SyncRecord.id)), 2
                    ).label('success_rate')
                ).group_by(SyncRecord.source_platform).all()
                
                # 按目标平台统计
                target_platform_stats = session.query(
                    SyncRecord.target_platform,
                    func.count(SyncRecord.id).label('total_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'success', 1), else_=0)).label('successful_syncs'),
                    func.round(
                        (func.sum(case((SyncRecord.sync_status == 'success', 1), else_=0)) * 100.0 / func.count(SyncRecord.id)), 2
                    ).label('success_rate')
                ).group_by(SyncRecord.target_platform).all()
                
                return {
                    "source_platforms": [
                        {
                            'source_platform': row.source_platform,
                            'total_syncs': row.total_syncs,
                            'successful_syncs': row.successful_syncs,
                            'success_rate': row.success_rate
                        } for row in source_platform_stats
                    ],
                    "target_platforms": [
                        {
                            'target_platform': row.target_platform,
                            'total_syncs': row.total_syncs,
                            'successful_syncs': row.successful_syncs,
                            'success_rate': row.success_rate
                        } for row in target_platform_stats
                    ]
                }
        except Exception as e:
            self.logger.error(f"获取平台统计失败: {e}")
            raise

    def get_realtime_data(self) -> Dict[str, Any]:
        """获取实时监控数据"""
        try:
            from database.connection import db
            from database.models import SyncRecord
            from sqlalchemy import func, and_
            from datetime import datetime, timedelta
            
            with db.get_session() as session:
                # 最近10分钟的同步活动
                ten_minutes_ago = datetime.now() - timedelta(minutes=10)
                recent_activity = session.query(
                    SyncRecord.sync_status,
                    func.count(SyncRecord.id).label('count')
                ).filter(
                    SyncRecord.created_at > ten_minutes_ago
                ).group_by(SyncRecord.sync_status).all()
                
                # 当前处理中的任务
                processing_tasks = session.query(
                    SyncRecord.source_platform,
                    SyncRecord.target_platform,
                    SyncRecord.created_at
                ).filter(
                    SyncRecord.sync_status == 'processing'
                ).order_by(SyncRecord.created_at.desc()).limit(5).all()
                
                # 最近的错误
                one_hour_ago = datetime.now() - timedelta(hours=1)
                recent_errors = session.query(
                    SyncRecord.source_platform,
                    SyncRecord.target_platform,
                    SyncRecord.error_message,
                    SyncRecord.created_at
                ).filter(
                    and_(
                        SyncRecord.sync_status == 'failed',
                        SyncRecord.created_at > one_hour_ago
                    )
                ).order_by(SyncRecord.created_at.desc()).limit(3).all()
                
                return {
                    "recent_activity": [
                        {'sync_status': row.sync_status, 'count': row.count} 
                        for row in recent_activity
                    ],
                    "processing_tasks": [
                        {
                            'source_platform': row.source_platform,
                            'target_platform': row.target_platform,
                            'created_at': str(row.created_at)
                        } for row in processing_tasks
                    ],
                    "recent_errors": [
                        {
                            'source_platform': row.source_platform,
                            'target_platform': row.target_platform,
                            'error_message': row.error_message,
                            'created_at': str(row.created_at)
                        } for row in recent_errors
                    ],
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        except Exception as e:
            self.logger.error(f"获取实时监控数据失败: {e}")
            raise

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """获取监控统计数据"""
        try:
            from database.connection import db
            from database.models import SyncRecord
            from sqlalchemy import func, case, and_
            from datetime import datetime, timedelta
            
            with db.get_session() as session:
                # 总体统计
                total_stats = session.query(
                    func.count(SyncRecord.id).label('total_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'success', 1), else_=0)).label('successful_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'failed', 1), else_=0)).label('failed_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'pending', 1), else_=0)).label('pending_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'processing', 1), else_=0)).label('processing_syncs')
                ).first()
                
                # 最近24小时统计
                twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
                recent_stats = session.query(
                    func.count(SyncRecord.id).label('total_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'success', 1), else_=0)).label('successful_syncs'),
                    func.sum(case((SyncRecord.sync_status == 'failed', 1), else_=0)).label('failed_syncs')
                ).filter(
                    SyncRecord.created_at > twenty_four_hours_ago
                ).first()
                
                # 平台使用情况
                platform_usage = session.query(
                    SyncRecord.source_platform,
                    SyncRecord.target_platform,
                    func.count(SyncRecord.id).label('count')
                ).group_by(
                    SyncRecord.source_platform, 
                    SyncRecord.target_platform
                ).order_by(func.count(SyncRecord.id).desc()).all()
                
                total_record = {
                    'total_syncs': total_stats.total_syncs,
                    'successful_syncs': total_stats.successful_syncs,
                    'failed_syncs': total_stats.failed_syncs,
                    'pending_syncs': total_stats.pending_syncs,
                    'processing_syncs': total_stats.processing_syncs
                }
                
                recent_record = {
                    'total_syncs': recent_stats.total_syncs,
                    'successful_syncs': recent_stats.successful_syncs,
                    'failed_syncs': recent_stats.failed_syncs
                }
                
                return {
                    "total_stats": total_record,
                    "recent_24h": recent_record,
                    "platform_usage": [
                        {
                            'source_platform': row.source_platform,
                            'target_platform': row.target_platform,
                            'count': row.count
                        } for row in platform_usage
                    ],
                    "success_rate": round((total_record['successful_syncs'] / max(total_record['total_syncs'], 1)) * 100, 2) if total_record['total_syncs'] > 0 else 0
                }
        except Exception as e:
            self.logger.error(f"获取监控统计失败: {e}")
            raise

    def get_images_list(self) -> Dict[str, Any]:
        """获取图片列表"""
        try:
            from database.connection import db
            from database.models import ImageMapping
            
            with db.get_session() as session:
                images = session.query(ImageMapping).order_by(
                    ImageMapping.created_at.desc()
                ).limit(100).all()
                
                return [
                    {
                        'id': img.id,
                        'filename': img.filename,
                        'original_url': img.original_url,
                        'qiniu_url': getattr(img, 'qiniu_url', None),
                        'local_path': img.local_path,
                        'size': img.size,
                        'mime_type': img.mime_type,
                        'file_hash': getattr(img, 'file_hash', None),
                        'created_at': str(img.created_at),
                        'sync_record_id': img.sync_record_id
                    } for img in images
                ]
        except Exception as e:
            self.logger.error(f"获取图片列表失败: {e}")
            raise

    def delete_image(self, image_id: int) -> Dict[str, Any]:
        """删除图片"""
        try:
            from database.connection import db
            from database.models import ImageMapping
            
            with db.get_session() as session:
                # 检查图片是否存在
                image = session.query(ImageMapping).filter(
                    ImageMapping.id == image_id
                ).first()
                
                if not image:
                    raise ValueError(f"图片 {image_id} 不存在")
                
                # 从数据库删除记录
                session.delete(image)
                session.commit()
                
                # TODO: 可以考虑从七牛云删除实际文件
                # qiniu_client.delete_file(image.local_path)
                
                return {
                    "message": "图片删除成功",
                    "deleted_image_id": image_id
                }
        except Exception as e:
            self.logger.error(f"删除图片失败: {e}")
            raise