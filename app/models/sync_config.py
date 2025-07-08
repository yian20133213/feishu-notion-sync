"""
Sync config CRUD operations
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from database.models import SyncConfig
from database.connection import get_db_session
import logging

logger = logging.getLogger(__name__)


class SyncConfigService:
    """同步配置服务"""
    
    @staticmethod
    def create_sync_config(
        platform: str,
        document_id: str,
        sync_direction: str,
        is_sync_enabled: bool = True,
        auto_sync: bool = True,
        notion_category: str = None
    ) -> SyncConfig:
        """创建同步配置"""
        from database.connection import db
        with db.get_session() as session:
            # 检查是否已存在相同的配置
            existing = session.query(SyncConfig).filter(
                and_(
                    SyncConfig.platform == platform,
                    SyncConfig.document_id == document_id
                )
            ).first()
            
            if existing:
                logger.info(f"Sync config already exists for {platform}:{document_id}")
                return existing
            
            config = SyncConfig(
                platform=platform,
                document_id=document_id,
                sync_direction=sync_direction,
                is_sync_enabled=is_sync_enabled,
                auto_sync=auto_sync,
                notion_category=notion_category
            )
            
            session.add(config)
            session.flush()
            session.refresh(config)
            
            # 在session关闭前提取数据
            config_data = {
                'id': config.id,
                'platform': config.platform,
                'document_id': config.document_id,
                'sync_direction': config.sync_direction,
                'is_sync_enabled': config.is_sync_enabled,
                'auto_sync': config.auto_sync,
                'notion_category': config.notion_category,
                'created_at': config.created_at,
                'updated_at': config.updated_at
            }
            
            logger.info(f"Created sync config for {platform}:{document_id}")
            
            # 创建一个新的对象返回，避免session问题
            from database.models import SyncConfig as SyncConfigModel
            result = SyncConfigModel()
            for key, value in config_data.items():
                setattr(result, key, value)
            
            return result
    
    @staticmethod
    def get_sync_config(config_id: int) -> Optional[SyncConfig]:
        """获取同步配置"""
        from database.connection import db
        with db.get_session() as session:
            config = session.query(SyncConfig).filter(SyncConfig.id == config_id).first()
            return config
    
    @staticmethod
    def get_sync_config_by_document(platform: str, document_id: str) -> Optional[SyncConfig]:
        """根据平台和文档ID获取同步配置"""
        from database.connection import db
        with db.get_session() as session:
            config = session.query(SyncConfig).filter(
                and_(
                    SyncConfig.platform == platform,
                    SyncConfig.document_id == document_id
                )
            ).first()
            return config
    
    @staticmethod
    def get_configs_by_platform(platform: str) -> List[SyncConfig]:
        """获取指定平台的所有配置"""
        from database.connection import db
        with db.get_session() as session:
            configs = session.query(SyncConfig).filter(
                SyncConfig.platform == platform
            ).order_by(desc(SyncConfig.updated_at)).all()
            
            logger.info(f"Retrieved {len(configs)} configs for platform {platform}")
            return configs
    
    @staticmethod
    def get_enabled_configs() -> List[SyncConfig]:
        """获取所有启用的同步配置"""
        from database.connection import db
        with db.get_session() as session:
            configs = session.query(SyncConfig).filter(
                SyncConfig.is_sync_enabled == True
            ).order_by(desc(SyncConfig.updated_at)).all()
            
            logger.info(f"Retrieved {len(configs)} enabled sync configs")
            return configs
    
    @staticmethod
    def get_auto_sync_configs() -> List[SyncConfig]:
        """获取所有自动同步配置"""
        from database.connection import db
        with db.get_session() as session:
            configs = session.query(SyncConfig).filter(
                and_(
                    SyncConfig.is_sync_enabled == True,
                    SyncConfig.auto_sync == True
                )
            ).order_by(desc(SyncConfig.updated_at)).all()
            
            logger.info(f"Retrieved {len(configs)} auto-sync configs")
            return configs
    
    @staticmethod
    def update_sync_config(
        config_id: int,
        is_sync_enabled: Optional[bool] = None,
        sync_direction: Optional[str] = None,
        auto_sync: Optional[bool] = None,
        notion_category: Optional[str] = None
    ) -> bool:
        """更新同步配置"""
        from database.connection import db
        with db.get_session() as session:
            config = session.query(SyncConfig).filter(SyncConfig.id == config_id).first()
            if not config:
                logger.error(f"Sync config {config_id} not found")
                return False
            
            if is_sync_enabled is not None:
                config.is_sync_enabled = is_sync_enabled
            
            if sync_direction is not None:
                config.sync_direction = sync_direction
            
            if auto_sync is not None:
                config.auto_sync = auto_sync
            
            if notion_category is not None:
                config.notion_category = notion_category
            
            logger.info(f"Updated sync config {config_id}")
            return True
    
    @staticmethod
    def enable_sync(platform: str, document_id: str) -> bool:
        """启用文档同步"""
        from database.connection import db
        with db.get_session() as session:
            config = session.query(SyncConfig).filter(
                and_(
                    SyncConfig.platform == platform,
                    SyncConfig.document_id == document_id
                )
            ).first()
            
            if not config:
                logger.error(f"Sync config not found for {platform}:{document_id}")
                return False
            
            config.is_sync_enabled = True
            logger.info(f"Enabled sync for {platform}:{document_id}")
            return True
    
    @staticmethod
    def disable_sync(platform: str, document_id: str) -> bool:
        """禁用文档同步"""
        from database.connection import db
        with db.get_session() as session:
            config = session.query(SyncConfig).filter(
                and_(
                    SyncConfig.platform == platform,
                    SyncConfig.document_id == document_id
                )
            ).first()
            
            if not config:
                logger.error(f"Sync config not found for {platform}:{document_id}")
                return False
            
            config.is_sync_enabled = False
            logger.info(f"Disabled sync for {platform}:{document_id}")
            return True
    
    @staticmethod
    def delete_sync_config(config_id: int) -> bool:
        """删除同步配置"""
        from database.connection import db
        with db.get_session() as session:
            config = session.query(SyncConfig).filter(SyncConfig.id == config_id).first()
            if not config:
                logger.error(f"Sync config {config_id} not found")
                return False
            
            session.delete(config)
            logger.info(f"Deleted sync config {config_id}")
            return True
    
    @staticmethod
    def delete_config_by_document(platform: str, document_id: str) -> bool:
        """根据平台和文档ID删除同步配置"""
        from database.connection import db
        with db.get_session() as session:
            config = session.query(SyncConfig).filter(
                and_(
                    SyncConfig.platform == platform,
                    SyncConfig.document_id == document_id
                )
            ).first()
            
            if not config:
                logger.warning(f"Sync config not found for {platform}:{document_id}")
                return False
            
            session.delete(config)
            logger.info(f"Deleted sync config for {platform}:{document_id}")
            return True
    
    @staticmethod
    def get_all_configs(limit: int = 100, offset: int = 0) -> List[SyncConfig]:
        """获取所有同步配置"""
        from database.connection import db
        with db.get_session() as session:
            configs = session.query(SyncConfig).order_by(
                desc(SyncConfig.updated_at)
            ).offset(offset).limit(limit).all()
            
            logger.info(f"Retrieved {len(configs)} sync configs")
            return configs
    
    @staticmethod
    def get_config_stats() -> Dict[str, Any]:
        """获取配置统计信息（优化版本）"""
        from database.connection import db
        from sqlalchemy import func, case
        
        with db.get_session() as session:
            # 使用单个查询获取所有统计信息
            stats_query = session.query(
                func.count(SyncConfig.id).label('total'),
                func.sum(case((SyncConfig.is_sync_enabled == True, 1), else_=0)).label('enabled'),
                func.sum(case((
                    and_(SyncConfig.is_sync_enabled == True, SyncConfig.auto_sync == True), 1
                ), else_=0)).label('auto_sync'),
                func.sum(case((SyncConfig.platform == 'feishu', 1), else_=0)).label('feishu_configs'),
                func.sum(case((SyncConfig.platform == 'notion', 1), else_=0)).label('notion_configs')
            ).first()
            
            total = stats_query.total or 0
            enabled = stats_query.enabled or 0
            
            stats = {
                "total": total,
                "enabled": enabled,
                "auto_sync": stats_query.auto_sync or 0,
                "feishu_configs": stats_query.feishu_configs or 0,
                "notion_configs": stats_query.notion_configs or 0,
                "enabled_rate": (enabled / total * 100) if total > 0 else 0
            }
            
            logger.info(f"Config stats: {stats}")
            return stats
    
    @staticmethod
    def is_sync_enabled(platform: str, document_id: str) -> bool:
        """检查文档是否启用同步"""
        from database.connection import db
        with db.get_session() as session:
            config = session.query(SyncConfig).filter(
                and_(
                    SyncConfig.platform == platform,
                    SyncConfig.document_id == document_id
                )
            ).first()
            
            if config:
                # 在session关闭前提取数据
                is_enabled = config.is_sync_enabled
                return is_enabled
            return False
    
    @staticmethod
    def is_auto_sync_enabled(platform: str, document_id: str) -> bool:
        """检查文档是否启用自动同步"""
        from database.connection import db
        with db.get_session() as session:
            config = session.query(SyncConfig).filter(
                and_(
                    SyncConfig.platform == platform,
                    SyncConfig.document_id == document_id
                )
            ).first()
            
            if config:
                # 在session关闭前提取数据
                is_enabled = config.is_sync_enabled
                auto_sync = config.auto_sync
                return is_enabled and auto_sync
            return False