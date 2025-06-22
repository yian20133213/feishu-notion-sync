"""
Image mapping CRUD operations
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database.models import ImageMapping
from database.connection import get_db_session
import logging

logger = logging.getLogger(__name__)


class ImageMappingService:
    """图片映射服务"""
    
    @staticmethod
    def create_image_mapping(
        original_url: str,
        qiniu_url: str,
        file_hash: str,
        file_size: int
    ) -> ImageMapping:
        """创建图片映射"""
        with next(get_db_session()) as db:
            # 检查是否已存在相同的映射
            existing = db.query(ImageMapping).filter(
                ImageMapping.file_hash == file_hash
            ).first()
            
            if existing:
                logger.info(f"Image mapping already exists for hash {file_hash}")
                return existing
            
            mapping = ImageMapping(
                original_url=original_url,
                qiniu_url=qiniu_url,
                file_hash=file_hash,
                file_size=file_size
            )
            
            db.add(mapping)
            db.flush()
            db.refresh(mapping)
            
            logger.info(f"Created image mapping: {original_url} -> {qiniu_url}")
            return mapping
    
    @staticmethod
    def get_image_mapping_by_url(original_url: str) -> Optional[ImageMapping]:
        """根据原始URL获取图片映射"""
        with next(get_db_session()) as db:
            mapping = db.query(ImageMapping).filter(
                ImageMapping.original_url == original_url
            ).first()
            return mapping
    
    @staticmethod
    def get_image_mapping_by_hash(file_hash: str) -> Optional[ImageMapping]:
        """根据文件哈希获取图片映射"""
        with next(get_db_session()) as db:
            mapping = db.query(ImageMapping).filter(
                ImageMapping.file_hash == file_hash
            ).first()
            return mapping
    
    @staticmethod
    def get_image_mapping(mapping_id: int) -> Optional[ImageMapping]:
        """获取图片映射"""
        with next(get_db_session()) as db:
            mapping = db.query(ImageMapping).filter(ImageMapping.id == mapping_id).first()
            return mapping
    
    @staticmethod
    def update_access_count(mapping_id: int) -> bool:
        """更新访问次数"""
        with next(get_db_session()) as db:
            mapping = db.query(ImageMapping).filter(ImageMapping.id == mapping_id).first()
            if not mapping:
                logger.error(f"Image mapping {mapping_id} not found")
                return False
            
            mapping.access_count += 1
            logger.debug(f"Updated access count for mapping {mapping_id}")
            return True
    
    @staticmethod
    def update_access_count_by_url(original_url: str) -> bool:
        """根据原始URL更新访问次数"""
        with next(get_db_session()) as db:
            mapping = db.query(ImageMapping).filter(
                ImageMapping.original_url == original_url
            ).first()
            
            if not mapping:
                logger.warning(f"Image mapping not found for URL: {original_url}")
                return False
            
            mapping.access_count += 1
            logger.debug(f"Updated access count for URL: {original_url}")
            return True
    
    @staticmethod
    def get_all_mappings(limit: int = 100, offset: int = 0) -> List[ImageMapping]:
        """获取所有图片映射"""
        with next(get_db_session()) as db:
            mappings = db.query(ImageMapping).order_by(
                desc(ImageMapping.upload_time)
            ).offset(offset).limit(limit).all()
            
            logger.info(f"Retrieved {len(mappings)} image mappings")
            return mappings
    
    @staticmethod
    def delete_image_mapping(mapping_id: int) -> bool:
        """删除图片映射"""
        with next(get_db_session()) as db:
            mapping = db.query(ImageMapping).filter(ImageMapping.id == mapping_id).first()
            if not mapping:
                logger.error(f"Image mapping {mapping_id} not found")
                return False
            
            db.delete(mapping)
            logger.info(f"Deleted image mapping {mapping_id}")
            return True
    
    @staticmethod
    def delete_mapping_by_url(original_url: str) -> bool:
        """根据原始URL删除图片映射"""
        with next(get_db_session()) as db:
            mapping = db.query(ImageMapping).filter(
                ImageMapping.original_url == original_url
            ).first()
            
            if not mapping:
                logger.warning(f"Image mapping not found for URL: {original_url}")
                return False
            
            db.delete(mapping)
            logger.info(f"Deleted image mapping for URL: {original_url}")
            return True
    
    @staticmethod
    def get_image_stats() -> Dict[str, Any]:
        """获取图片统计信息"""
        with next(get_db_session()) as db:
            total_images = db.query(ImageMapping).count()
            total_size = db.query(func.sum(ImageMapping.file_size)).scalar() or 0
            total_access = db.query(func.sum(ImageMapping.access_count)).scalar() or 0
            avg_size = db.query(func.avg(ImageMapping.file_size)).scalar() or 0
            
            stats = {
                "total_images": total_images,
                "total_size": total_size,
                "total_access": total_access,
                "avg_size": round(avg_size, 2) if avg_size else 0,
                "size_mb": round(total_size / (1024 * 1024), 2)
            }
            
            logger.info(f"Image stats: {stats}")
            return stats
    
    @staticmethod
    def get_popular_images(limit: int = 10) -> List[ImageMapping]:
        """获取访问次数最多的图片"""
        with next(get_db_session()) as db:
            mappings = db.query(ImageMapping).order_by(
                desc(ImageMapping.access_count)
            ).limit(limit).all()
            
            logger.info(f"Retrieved top {len(mappings)} popular images")
            return mappings
    
    @staticmethod
    def search_images(query: str, limit: int = 50) -> List[ImageMapping]:
        """搜索图片映射"""
        with next(get_db_session()) as db:
            mappings = db.query(ImageMapping).filter(
                (ImageMapping.original_url.contains(query)) |
                (ImageMapping.qiniu_url.contains(query))
            ).order_by(desc(ImageMapping.upload_time)).limit(limit).all()
            
            logger.info(f"Found {len(mappings)} images matching query: {query}")
            return mappings