"""
Database models for the sync system
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, Index
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from .connection import Base


class SyncRecord(Base):
    """同步记录表"""
    __tablename__ = "sync_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_platform = Column(String(20), nullable=False)  # 'feishu' or 'notion'
    target_platform = Column(String(20), nullable=False)
    source_id = Column(String(100), nullable=False)       # 源文档ID
    target_id = Column(String(100), nullable=True)        # 目标文档ID
    content_type = Column(String(20), nullable=False)     # 'document', 'database', 'page'
    sync_status = Column(String(20), nullable=False)      # 'pending', 'processing', 'success', 'failed'
    last_sync_time = Column(TIMESTAMP, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SyncRecord(id={self.id}, {self.source_platform}->{self.target_platform}, status={self.sync_status})>"


class ImageMapping(Base):
    """图片映射表"""
    __tablename__ = "image_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_url = Column(String(500), nullable=False)
    qiniu_url = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=False)        # MD5校验和
    file_size = Column(Integer, nullable=False)
    upload_time = Column(TIMESTAMP, nullable=False, default=func.now())
    access_count = Column(Integer, nullable=False, default=0)
    
    # 创建索引
    __table_args__ = (
        Index('idx_original_url', 'original_url'),
        Index('idx_file_hash', 'file_hash'),
    )
    
    def __repr__(self):
        return f"<ImageMapping(id={self.id}, hash={self.file_hash[:8]}..., size={self.file_size})>"


class SyncConfig(Base):
    """同步配置表"""
    __tablename__ = "sync_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False)
    document_id = Column(String(100), nullable=False)
    is_sync_enabled = Column(Boolean, nullable=False, default=True)
    sync_direction = Column(String(20), nullable=False)   # 'feishu_to_notion', 'notion_to_feishu', 'bidirectional'
    auto_sync = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SyncConfig(id={self.id}, platform={self.platform}, document_id={self.document_id})>"