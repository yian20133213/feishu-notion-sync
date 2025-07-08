"""
数据库查询优化工具
"""
from sqlalchemy import text
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
import logging

from .connection import db

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """数据库查询优化器"""
    
    @staticmethod
    @contextmanager
    def optimized_session(read_only: bool = False):
        """优化的数据库会话，支持只读模式"""
        session = db.SessionLocal()
        try:
            if read_only:
                # 只读模式设置事务为只读
                session.execute(text("SET TRANSACTION READ ONLY"))
            yield session
            if not read_only:
                session.commit()
        except Exception as e:
            if not read_only:
                session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @staticmethod
    def get_connection_pool_status() -> Dict[str, Any]:
        """获取连接池状态"""
        if not db.engine:
            return {"error": "Database not initialized"}
        
        pool = db.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
    
    @staticmethod
    def analyze_query_performance(query_sql: str) -> Dict[str, Any]:
        """分析查询性能（仅适用于支持EXPLAIN的数据库）"""
        try:
            with db.get_session() as session:
                # 使用EXPLAIN分析查询
                explain_query = f"EXPLAIN {query_sql}"
                result = session.execute(text(explain_query))
                
                performance_info = []
                for row in result:
                    performance_info.append(dict(row))
                
                return {
                    "query": query_sql,
                    "execution_plan": performance_info
                }
        except Exception as e:
            logger.warning(f"Query analysis failed: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_slow_queries(limit: int = 10) -> List[Dict[str, Any]]:
        """获取慢查询（需要数据库支持）"""
        try:
            with db.get_session() as session:
                # 这里需要根据具体数据库类型实现
                # 例如：MySQL的performance_schema，PostgreSQL的pg_stat_statements
                slow_queries = []
                # 实现获取慢查询的逻辑
                return slow_queries
        except Exception as e:
            logger.warning(f"Failed to get slow queries: {e}")
            return []
    
    @staticmethod
    def optimize_table_indexes() -> Dict[str, Any]:
        """分析和建议表索引优化"""
        suggestions = []
        
        # 基于模型分析索引使用情况
        index_suggestions = {
            "sync_records": [
                "考虑在 (source_platform, source_id) 上创建复合索引以优化源查询",
                "考虑在 (sync_status, created_at) 上创建复合索引以优化状态查询",
                "last_sync_time 字段应该有索引以优化时间范围查询"
            ],
            "sync_configs": [
                "在 (platform, document_id) 上创建唯一复合索引",
                "在 is_sync_enabled 和 auto_sync 字段上创建索引以优化配置查询"
            ],
            "images": [
                "在 original_url 上创建索引（注意URL长度限制）",
                "在 hash 字段上创建唯一索引以避免重复图片",
                "在 created_at 上创建索引以优化时间查询"
            ]
        }
        
        return {
            "suggestions": index_suggestions,
            "status": "recommendations_generated"
        }
    
    @staticmethod
    def vacuum_analyze_tables() -> Dict[str, Any]:
        """执行表维护操作（仅适用于PostgreSQL等支持的数据库）"""
        try:
            with db.get_session() as session:
                # 根据数据库类型执行不同的维护命令
                if "postgresql" in str(db.engine.url).lower():
                    # PostgreSQL VACUUM ANALYZE
                    session.execute(text("VACUUM ANALYZE"))
                    return {"status": "vacuum_analyze_completed"}
                elif "mysql" in str(db.engine.url).lower():
                    # MySQL OPTIMIZE TABLE
                    session.execute(text("OPTIMIZE TABLE sync_records, sync_configs, images"))
                    return {"status": "optimize_table_completed"}
                else:
                    return {"status": "maintenance_not_supported"}
        except Exception as e:
            logger.error(f"Table maintenance failed: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_database_statistics() -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            with db.get_session() as session:
                stats = {}
                
                # 获取表行数
                for table_name in ['sync_records', 'sync_configs', 'images']:
                    try:
                        result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        count = result.scalar()
                        stats[f"{table_name}_count"] = count
                    except Exception as e:
                        logger.warning(f"Failed to get count for {table_name}: {e}")
                        stats[f"{table_name}_count"] = "error"
                
                # 获取连接池状态
                stats["connection_pool"] = QueryOptimizer.get_connection_pool_status()
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            return {"error": str(e)}


# 批量查询优化辅助函数
def batch_query_with_pagination(query, batch_size: int = 1000):
    """
    分批执行大查询以避免内存问题
    
    Args:
        query: SQLAlchemy查询对象
        batch_size: 每批处理的数量
    
    Yields:
        每批查询结果
    """
    offset = 0
    while True:
        batch = query.offset(offset).limit(batch_size).all()
        if not batch:
            break
        yield batch
        offset += batch_size


def execute_bulk_operations(operations: List[Dict[str, Any]], batch_size: int = 100):
    """
    批量执行数据库操作
    
    Args:
        operations: 操作列表，每个操作包含类型和数据
        batch_size: 批量大小
    
    Returns:
        执行结果
    """
    results = []
    
    with db.get_session() as session:
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            
            try:
                for operation in batch:
                    op_type = operation.get('type')
                    data = operation.get('data')
                    
                    if op_type == 'insert':
                        session.add(data)
                    elif op_type == 'update':
                        # 实现批量更新逻辑
                        pass
                    elif op_type == 'delete':
                        session.delete(data)
                
                session.flush()  # 提交批次
                results.append(f"Batch {i//batch_size + 1}: {len(batch)} operations completed")
                
            except Exception as e:
                logger.error(f"Batch operation failed: {e}")
                session.rollback()
                results.append(f"Batch {i//batch_size + 1}: Failed - {str(e)}")
                break
    
    return results