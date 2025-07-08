#!/usr/bin/env python3
"""
同步服务层 - 处理所有同步相关的业务逻辑
"""
import os
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import sqlite3
import logging

# 定义项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class SyncService:
    """同步服务类 - 处理同步相关的核心业务逻辑"""
    
    def __init__(self, logger: logging.Logger = None, db_path: str = None):
        self.logger = logger or logging.getLogger(__name__)
        self.db_path = db_path or os.path.join(PROJECT_ROOT, 'feishu_notion_sync.db')
    
    @contextmanager
    def get_db_session(self):
        """数据库会话上下文管理器"""
        from database.connection import db
        with db.get_session() as session:
            yield session
    
    def format_datetime(self, dt: datetime = None) -> str:
        """统一日期时间格式处理"""
        if isinstance(dt, str):
            return dt
        elif isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def safe_row_to_dict(self, row, default_values: Dict = None) -> Dict:
        """安全地将数据库行转换为字典"""
        if row is None:
            return default_values or {}
        
        result = dict(row)
        
        # 处理日期时间字段
        for key, value in result.items():
            if key in ['created_at', 'updated_at', 'last_sync_time'] and value:
                try:
                    if isinstance(value, str) and 'T' in value:
                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        result[key] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, datetime):
                        result[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, AttributeError):
                    pass
        
        # 合并默认值
        if default_values:
            for key, default_value in default_values.items():
                if key not in result or result[key] is None:
                    result[key] = default_value
        
        return result
    
    def generate_record_number(self) -> str:
        """生成唯一记录编号"""
        timestamp = int(time.time())
        random_suffix = random.randint(100, 999)
        return f"{timestamp}_{random_suffix}"
    
    # ==================== 同步配置管理 ====================
    
    def get_sync_configs(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """获取同步配置列表"""
        try:
            from database.models import SyncConfig
            
            per_page = min(per_page, 50)  # 限制最大每页数量
            offset = (page - 1) * per_page
            
            with self.get_db_session() as session:
                # 获取总数
                total = session.query(SyncConfig).count()
                
                # 获取分页数据
                configs = session.query(SyncConfig).order_by(
                    SyncConfig.created_at.desc()
                ).offset(offset).limit(per_page).all()
                
                config_list = []
                for config in configs:
                    config_dict = {
                        'id': config.id,
                        'platform': config.platform,
                        'document_id': config.document_id,
                        'sync_direction': config.sync_direction,
                        'is_sync_enabled': config.is_sync_enabled,
                        'auto_sync': config.auto_sync,
                        'webhook_url': config.webhook_url,
                        'created_at': self.format_datetime(config.created_at),
                        'updated_at': self.format_datetime(config.updated_at)
                    }
                    config_list.append(config_dict)
                
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
            
            with self.get_db_connection() as conn:
                # 检查是否已存在相同配置
                existing = conn.execute('''
                    SELECT id FROM sync_configs 
                    WHERE platform = ? AND document_id = ?
                ''', (platform, document_id)).fetchone()
                
                if existing:
                    raise ValueError("该文档的同步配置已存在")
                
                # 创建新配置
                cursor = conn.execute('''
                    INSERT INTO sync_configs (platform, document_id, sync_direction, 
                                            is_sync_enabled, auto_sync, webhook_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    platform,
                    document_id,
                    sync_direction,
                    config_data.get('is_sync_enabled', True),
                    config_data.get('auto_sync', True),
                    config_data.get('webhook_url'),
                    self.format_datetime(),
                    self.format_datetime()
                ))
                
                config_id = cursor.lastrowid
                conn.commit()
                
                return {"config_id": config_id, "message": "同步配置创建成功"}
                
        except Exception as e:
            self.logger.error(f"创建同步配置失败: {e}")
            raise
    
    def update_sync_config(self, config_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新同步配置"""
        try:
            with self.get_db_connection() as conn:
                # 检查配置是否存在
                existing = conn.execute('SELECT * FROM sync_configs WHERE id = ?', (config_id,)).fetchone()
                if not existing:
                    raise ValueError("配置不存在")
                
                # 构建更新字段
                update_fields = []
                update_values = []
                
                for field in ['is_sync_enabled', 'auto_sync', 'webhook_url']:
                    if field in update_data:
                        update_fields.append(f"{field} = ?")
                        update_values.append(update_data[field])
                
                if not update_fields:
                    raise ValueError("没有提供要更新的字段")
                
                update_fields.append("updated_at = ?")
                update_values.append(self.format_datetime())
                update_values.append(config_id)
                
                # 执行更新
                conn.execute(f'''
                    UPDATE sync_configs SET {', '.join(update_fields)}
                    WHERE id = ?
                ''', update_values)
                
                conn.commit()
                
                return {"message": "配置更新成功"}
                
        except Exception as e:
            self.logger.error(f"更新同步配置失败: {e}")
            raise
    
    def get_sync_config_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取单个同步配置"""
        try:
            with self.get_db_connection() as conn:
                config = conn.execute('''
                    SELECT * FROM sync_configs WHERE id = ?
                ''', (config_id,)).fetchone()
                
                if not config:
                    return None
                
                return self.safe_row_to_dict(config)
        except Exception as e:
            self.logger.error(f"获取同步配置失败: {e}")
            raise
    
    def delete_sync_config(self, config_id: int) -> Dict[str, Any]:
        """删除同步配置"""
        try:
            with self.get_db_connection() as conn:
                result = conn.execute('DELETE FROM sync_configs WHERE id = ?', (config_id,))
                conn.commit()
                
                if result.rowcount == 0:
                    raise ValueError("配置不存在")
                
                return {"message": "配置已删除"}
        except Exception as e:
            self.logger.error(f"删除同步配置失败: {e}")
            raise
    
    # ==================== 同步记录管理 ====================
    
    def get_sync_records(self, page: int = 1, per_page: int = 20, status: str = None, platform: str = None) -> Dict[str, Any]:
        """获取同步记录列表"""
        try:
            per_page = min(per_page, 100)
            offset = (page - 1) * per_page
            
            # 构建查询条件
            where_conditions = []
            params = []
            
            if status:
                where_conditions.append("sync_status = ?")
                params.append(status)
            
            if platform:
                where_conditions.append("source_platform = ?")
                params.append(platform)
            
            where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
            
            with self.get_db_connection() as conn:
                # 获取总数
                count_query = f"SELECT COUNT(*) as total FROM sync_records {where_clause}"
                total = conn.execute(count_query, params).fetchone()['total']
                
                # 获取分页数据
                records_query = f'''
                    SELECT id, record_number, source_platform, target_platform, source_id, 
                           target_id, content_type, sync_status, error_message, 
                           created_at, updated_at, last_sync_time
                    FROM sync_records 
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                '''
                
                records = conn.execute(records_query, params + [per_page, offset]).fetchall()
                records_list = [self.safe_row_to_dict(record) for record in records]
                
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
            
            with self.get_db_connection() as conn:
                for doc_id in document_ids:
                    try:
                        # 检查是否已存在同步记录
                        existing_record = conn.execute('''
                            SELECT id, sync_status FROM sync_records 
                            WHERE source_platform = 'feishu' AND source_id = ?
                            ORDER BY created_at DESC LIMIT 1
                        ''', (doc_id,)).fetchone()
                        
                        if existing_record and not force_sync:
                            if existing_record['sync_status'] in ['pending', 'processing']:
                                created_records.append({
                                    'document_id': doc_id,
                                    'record_id': existing_record['id'],
                                    'status': 'exists',
                                    'message': '同步任务已存在，正在处理中'
                                })
                                continue
                        
                        # 创建新的同步记录
                        record_number = self.generate_record_number()
                        cursor = conn.execute('''
                            INSERT INTO sync_records (record_number, source_platform, target_platform, 
                                                    source_id, content_type, sync_status, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            record_number,
                            'feishu',
                            'notion',
                            doc_id,
                            'document',
                            'pending',
                            self.format_datetime(),
                            self.format_datetime()
                        ))
                        
                        record_id = cursor.lastrowid
                        created_records.append({
                            'document_id': doc_id,
                            'record_id': record_id,
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
                
                conn.commit()
            
            # 统计结果
            created_count = len([r for r in created_records if r['status'] == 'created'])
            exists_count = len([r for r in created_records if r['status'] == 'exists'])
            error_count = len([r for r in created_records if r['status'] == 'error'])
            
            return {
                'total_requested': len(document_ids),
                'created_count': created_count,
                'exists_count': exists_count,
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
            
            with self.get_db_connection() as conn:
                if record_ids:
                    if len(record_ids) > 100:
                        raise ValueError("单次最多只能删除100条记录")
                    
                    placeholders = ','.join(['?' for _ in record_ids])
                    result = conn.execute(f'DELETE FROM sync_records WHERE id IN ({placeholders})', record_ids)
                    deleted_count = result.rowcount
                
                elif status:
                    if status not in ['failed', 'completed', 'pending']:
                        raise ValueError("无效的状态值")
                    
                    result = conn.execute('DELETE FROM sync_records WHERE sync_status = ?', (status,))
                    deleted_count = result.rowcount
                
                conn.commit()
                
                return {
                    "message": f"成功删除 {deleted_count} 条记录",
                    "deleted_count": deleted_count
                }
                
        except Exception as e:
            self.logger.error(f"批量删除同步记录失败: {e}")
            raise
    
    def retry_sync_records_batch(self, record_ids: List[int], retry_failed_only: bool = True) -> Dict[str, Any]:
        """批量重试同步记录"""
        try:
            if not record_ids:
                raise ValueError("请提供要重试的记录ID")
            
            if len(record_ids) > 100:
                raise ValueError("单次最多只能重试100条记录")
            
            with self.get_db_connection() as conn:
                # 构建查询条件
                placeholders = ','.join(['?' for _ in record_ids])
                where_clause = f"id IN ({placeholders})"
                params = record_ids.copy()
                
                if retry_failed_only:
                    where_clause += " AND sync_status = ?"
                    params.append('failed')
                
                # 更新记录状态
                result = conn.execute(f'''
                    UPDATE sync_records SET 
                        sync_status = 'pending',
                        error_message = NULL,
                        updated_at = ?
                    WHERE {where_clause}
                ''', [self.format_datetime()] + params)
                
                updated_count = result.rowcount
                conn.commit()
                
                return {
                    "message": f"成功提交 {updated_count} 个重试任务",
                    "updated_count": updated_count
                }
                
        except Exception as e:
            self.logger.error(f"批量重试同步记录失败: {e}")
            raise
    
    def retry_sync_record(self, record_id: int) -> Dict[str, Any]:
        """重试单个同步记录"""
        try:
            with self.get_db_connection() as conn:
                # 检查记录是否存在
                record = conn.execute('SELECT * FROM sync_records WHERE id = ?', (record_id,)).fetchone()
                if not record:
                    raise ValueError("记录不存在")
                
                # 更新状态为pending以重新处理
                conn.execute('''
                    UPDATE sync_records SET 
                        sync_status = 'pending',
                        error_message = NULL,
                        updated_at = ?
                    WHERE id = ?
                ''', (self.format_datetime(), record_id))
                
                conn.commit()
                
                return {"message": "重试任务已提交"}
                
        except Exception as e:
            self.logger.error(f"重试同步记录失败: {e}")
            raise
    
    # ==================== 统计和监控 ====================
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """获取仪表板统计数据"""
        try:
            with self.get_db_connection() as conn:
                # 获取基本统计
                total_configs = conn.execute('SELECT COUNT(*) as count FROM sync_configs').fetchone()['count']
                active_configs = conn.execute('SELECT COUNT(*) as count FROM sync_configs WHERE is_sync_enabled = 1').fetchone()['count']
                
                # 获取同步记录统计
                total_records = conn.execute('SELECT COUNT(*) as count FROM sync_records').fetchone()['count']
                success_records = conn.execute('SELECT COUNT(*) as count FROM sync_records WHERE sync_status = "success"').fetchone()['count']
                failed_records = conn.execute('SELECT COUNT(*) as count FROM sync_records WHERE sync_status = "failed"').fetchone()['count']
                pending_records = conn.execute('SELECT COUNT(*) as count FROM sync_records WHERE sync_status = "pending"').fetchone()['count']
                
                # 计算成功率
                success_rate = (success_records / total_records * 100) if total_records > 0 else 0
                
                return {
                    "total_configs": total_configs,
                    "active_configs": active_configs,
                    "total_records": total_records,
                    "success_records": success_records,
                    "failed_records": failed_records,
                    "pending_records": pending_records,
                    "success_rate": round(success_rate, 2)
                }
        except Exception as e:
            self.logger.error(f"获取仪表板统计失败: {e}")
            raise
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能监控指标"""
        try:
            with self.get_db_connection() as conn:
                # 获取各种统计数据
                stats = {}
                
                # 同步状态统计
                status_stats = conn.execute('''
                    SELECT sync_status, COUNT(*) as count 
                    FROM sync_records 
                    GROUP BY sync_status
                ''').fetchall()
                
                stats['sync_status'] = {row['sync_status']: row['count'] for row in status_stats}
                
                # 最近24小时同步数量
                stats['recent_syncs'] = conn.execute('''
                    SELECT COUNT(*) as count FROM sync_records 
                    WHERE created_at > datetime('now', '-24 hours')
                ''').fetchone()['count']
                
                # 成功率统计
                total_syncs = conn.execute('SELECT COUNT(*) as count FROM sync_records').fetchone()['count']
                successful_syncs = conn.execute('''
                    SELECT COUNT(*) as count FROM sync_records WHERE sync_status = 'success'
                ''').fetchone()['count']
                
                stats['success_rate'] = (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0
                
                return stats
                
        except Exception as e:
            self.logger.error(f"获取性能指标失败: {e}")
            raise
    
    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取同步历史记录"""
        try:
            with self.get_db_connection() as conn:
                records = conn.execute('''
                    SELECT record_number, source_platform, target_platform, source_id, 
                           sync_status, last_sync_time, error_message, created_at
                    FROM sync_records 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,)).fetchall()
                
                return [self.safe_row_to_dict(record) for record in records]
        except Exception as e:
            self.logger.error(f"获取同步历史失败: {e}")
            raise
    
    def delete_sync_record(self, record_id: int) -> Dict[str, Any]:
        """删除单个同步记录"""
        try:
            with self.get_db_connection() as conn:
                # 检查记录是否存在
                record = conn.execute('SELECT id FROM sync_records WHERE id = ?', (record_id,)).fetchone()
                if not record:
                    raise ValueError("记录不存在")
                
                # 删除记录
                result = conn.execute('DELETE FROM sync_records WHERE id = ?', (record_id,))
                conn.commit()
                
                if result.rowcount == 0:
                    raise ValueError("删除失败，记录可能已被删除")
                
                return {"message": "记录已删除"}
                
        except Exception as e:
            self.logger.error(f"删除同步记录失败: {e}")
            raise
    
    def get_sync_record_detail(self, record_id: int) -> Dict[str, Any]:
        """获取单个同步记录详情"""
        try:
            with self.get_db_connection() as conn:
                record = conn.execute('''
                    SELECT id, record_number, source_platform, target_platform, 
                           source_id, target_id, content_type, sync_status, 
                           error_message, created_at, updated_at, last_sync_time
                    FROM sync_records 
                    WHERE id = ?
                ''', (record_id,)).fetchone()
                
                if not record:
                    raise ValueError("记录不存在")
                
                return self.safe_row_to_dict(record)
                
        except Exception as e:
            self.logger.error(f"获取同步记录详情失败: {e}")
            raise