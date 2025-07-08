#!/usr/bin/env python3
"""
Database migration service to transition from raw SQLite to SQLAlchemy
"""
import os
import sys
import sqlite3
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import db
from database.models import Base
from config.settings import settings

logger = logging.getLogger(__name__)


class MigrationService:
    """服务于从原生SQLite到SQLAlchemy的迁移"""
    
    def __init__(self):
        self.old_db_path = os.path.join(PROJECT_ROOT, 'feishu_notion_sync.db')
        
    def check_old_database_exists(self) -> bool:
        """检查旧数据库是否存在"""
        return os.path.exists(self.old_db_path)
    
    def get_old_database_schema(self) -> dict:
        """获取旧数据库的表结构"""
        if not self.check_old_database_exists():
            return {}
        
        schema = {}
        try:
            conn = sqlite3.connect(self.old_db_path)
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table_name, in tables:
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                schema[table_name] = columns
            
            conn.close()
            return schema
        except Exception as e:
            logger.error(f"获取旧数据库架构失败: {e}")
            return {}
    
    def migrate_data(self, backup_old: bool = True) -> bool:
        """迁移数据从旧数据库到新数据库"""
        try:
            if not self.check_old_database_exists():
                logger.info("旧数据库不存在，创建新数据库")
                db.create_tables()
                return True
            
            # 备份旧数据库
            if backup_old:
                backup_path = f"{self.old_db_path}.backup"
                import shutil
                shutil.copy2(self.old_db_path, backup_path)
                logger.info(f"已备份旧数据库到: {backup_path}")
            
            # 初始化新数据库
            db.initialize()
            db.create_tables()
            
            # 连接旧数据库
            old_conn = sqlite3.connect(self.old_db_path)
            old_conn.row_factory = sqlite3.Row
            
            # 迁移sync_configs表
            self._migrate_sync_configs(old_conn)
            
            # 迁移sync_records表
            self._migrate_sync_records(old_conn)
            
            # 迁移images表
            self._migrate_images(old_conn)
            
            old_conn.close()
            
            logger.info("数据迁移完成")
            return True
            
        except Exception as e:
            logger.error(f"数据迁移失败: {e}")
            return False
    
    def _migrate_sync_configs(self, old_conn):
        """迁移sync_configs表"""
        try:
            cursor = old_conn.cursor()
            cursor.execute("SELECT * FROM sync_configs")
            configs = cursor.fetchall()
            
            with db.get_session() as session:
                from database.models import SyncConfig
                
                for config in configs:
                    new_config = SyncConfig(
                        id=config['id'],
                        platform=config['platform'],
                        document_id=config['document_id'],
                        sync_direction=config['sync_direction'] if 'sync_direction' in config.keys() else 'bidirectional',
                        is_sync_enabled=bool(config['is_sync_enabled'] if 'is_sync_enabled' in config.keys() else 1),
                        auto_sync=bool(config['auto_sync'] if 'auto_sync' in config.keys() else 1),
                        webhook_url=config['webhook_url'] if 'webhook_url' in config.keys() else None,
                        created_at=config['created_at'] if 'created_at' in config.keys() else None,
                        updated_at=config['updated_at'] if 'updated_at' in config.keys() else None
                    )
                    session.merge(new_config)  # 使用merge避免重复
                
                session.commit()
            
            logger.info(f"迁移了 {len(configs)} 个同步配置")
            
        except Exception as e:
            logger.error(f"迁移sync_configs失败: {e}")
    
    def _migrate_sync_records(self, old_conn):
        """迁移sync_records表"""
        try:
            cursor = old_conn.cursor()
            cursor.execute("SELECT * FROM sync_records")
            records = cursor.fetchall()
            
            with db.get_session() as session:
                from database.models import SyncRecord
                
                for record in records:
                    new_record = SyncRecord(
                        id=record['id'],
                        record_number=record['record_number'] if 'record_number' in record.keys() else None,
                        source_platform=record['source_platform'],
                        target_platform=record['target_platform'],
                        source_id=record['source_id'],
                        target_id=record['target_id'] if 'target_id' in record.keys() else None,
                        content_type=record['content_type'] if 'content_type' in record.keys() else 'document',
                        sync_status=record['sync_status'] if 'sync_status' in record.keys() else 'pending',
                        last_sync_time=record['last_sync_time'] if 'last_sync_time' in record.keys() else None,
                        error_message=record['error_message'] if 'error_message' in record.keys() else None,
                        created_at=record['created_at'] if 'created_at' in record.keys() else None,
                        updated_at=record['updated_at'] if 'updated_at' in record.keys() else None
                    )
                    session.merge(new_record)
                
                session.commit()
            
            logger.info(f"迁移了 {len(records)} 个同步记录")
            
        except Exception as e:
            logger.error(f"迁移sync_records失败: {e}")
    
    def _migrate_images(self, old_conn):
        """迁移images表"""
        try:
            cursor = old_conn.cursor()
            cursor.execute("SELECT * FROM images")
            images = cursor.fetchall()
            
            with db.get_session() as session:
                from database.models import ImageMapping
                
                for image in images:
                    new_image = ImageMapping(
                        id=image['id'],
                        filename=image['filename'],
                        original_url=image['original_url'] if 'original_url' in image.keys() else None,
                        local_path=image['local_path'] if 'local_path' in image.keys() else None,
                        size=image['size'] if 'size' in image.keys() else None,
                        mime_type=image['mime_type'] if 'mime_type' in image.keys() else None,
                        hash=image['hash'] if 'hash' in image.keys() else None,
                        created_at=image['created_at'] if 'created_at' in image.keys() else None,
                        sync_record_id=image['sync_record_id'] if 'sync_record_id' in image.keys() else None
                    )
                    session.merge(new_image)
                
                session.commit()
            
            logger.info(f"迁移了 {len(images)} 个图片记录")
            
        except Exception as e:
            logger.error(f"迁移images失败: {e}")
    
    def cleanup_old_database_code(self):
        """清理旧的数据库代码 - 只是标记，不实际删除"""
        logger.info("请手动删除 app/core/database.py 中的原生SQLite实现")
        logger.info("并更新所有使用旧数据库接口的代码")


def main():
    """主迁移函数"""
    logging.basicConfig(level=logging.INFO)
    
    migration_service = MigrationService()
    
    print("开始数据库迁移...")
    print(f"检查旧数据库: {migration_service.old_db_path}")
    
    if migration_service.check_old_database_exists():
        schema = migration_service.get_old_database_schema()
        print(f"发现旧数据库，包含表: {list(schema.keys())}")
        
        # 执行迁移
        if migration_service.migrate_data():
            print("✅ 数据迁移成功完成")
        else:
            print("❌ 数据迁移失败")
            return False
    else:
        print("未发现旧数据库，创建新数据库...")
        db.create_tables()
        print("✅ 新数据库创建完成")
    
    print("\n迁移完成。下一步:")
    print("1. 更新应用代码使用新的SQLAlchemy模型")
    print("2. 删除旧的app/core/database.py文件")
    print("3. 运行测试确保一切正常")
    
    return True


if __name__ == "__main__":
    main()