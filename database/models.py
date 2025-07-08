"""
Database models for the sync system
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, Index
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from .connection import Base, CompatibleTimestamp


class SyncRecord(Base):
    """同步记录表"""
    __tablename__ = "sync_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_number = Column(String(50), nullable=True, unique=True)  # 记录编号
    source_platform = Column(String(20), nullable=False)  # 'feishu' or 'notion'
    target_platform = Column(String(20), nullable=False)
    source_id = Column(String(100), nullable=False)       # 源文档ID
    target_id = Column(String(100), nullable=True)        # 目标文档ID
    content_type = Column(String(20), nullable=False, default='document')     # 'document', 'database', 'page'
    sync_status = Column(String(20), nullable=False, default='pending')      # 'pending', 'processing', 'success', 'failed'
    last_sync_time = Column(CompatibleTimestamp, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(CompatibleTimestamp, nullable=False, default=func.now())
    updated_at = Column(CompatibleTimestamp, nullable=False, default=func.now(), onupdate=func.now())
    
    # 添加复合索引以优化查询性能
    __table_args__ = (
        Index('idx_sync_status_created', 'sync_status', 'created_at'),
        Index('idx_source_platform_id', 'source_platform', 'source_id'),
        Index('idx_target_platform_id', 'target_platform', 'target_id'),
        Index('idx_sync_time', 'last_sync_time'),
        # 添加复合索引来优化重复检查查询
        Index('idx_sync_duplicate_check', 'source_platform', 'target_platform', 'source_id', 'sync_status'),
    )
    
    def __repr__(self):
        return f"<SyncRecord(id={self.id}, {self.source_platform}->{self.target_platform}, status={self.sync_status})>"


class ImageMapping(Base):
    """图片映射表"""
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_url = Column(String(500), nullable=True)
    local_path = Column(String(500), nullable=True)
    size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    hash = Column(String(64), nullable=True)        # MD5校验和
    created_at = Column(CompatibleTimestamp, nullable=False, default=func.now())
    sync_record_id = Column(Integer, nullable=True)  # 外键引用sync_records
    
    # 优化索引结构
    __table_args__ = (
        Index('idx_images_sync_record', 'sync_record_id'),
        Index('idx_original_url', 'original_url', mysql_length=255),  # 限制索引长度
        Index('idx_file_hash', 'hash'),
        Index('idx_created_at', 'created_at'),  # 添加时间索引
        Index('idx_filename', 'filename'),  # 添加文件名索引
    )
    
    def __repr__(self):
        return f"<ImageMapping(id={self.id}, filename={self.filename}, size={self.size})>"


class SyncConfig(Base):
    """同步配置表"""
    __tablename__ = "sync_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False)
    document_id = Column(String(100), nullable=False)
    sync_direction = Column(String(20), nullable=False, default='bidirectional')   # 'feishu_to_notion', 'notion_to_feishu', 'bidirectional'
    is_sync_enabled = Column(Boolean, nullable=False, default=True)
    auto_sync = Column(Boolean, nullable=False, default=True)
    webhook_url = Column(String(500), nullable=True)  # 添加webhook_url字段
    notion_category = Column(String(50), nullable=True)  # 添加Notion分类字段
    created_at = Column(CompatibleTimestamp, nullable=False, default=func.now())
    updated_at = Column(CompatibleTimestamp, nullable=False, default=func.now(), onupdate=func.now())
    
    # 添加索引优化配置查询
    __table_args__ = (
        Index('idx_platform_document', 'platform', 'document_id'),
        Index('idx_sync_enabled', 'is_sync_enabled'),
        Index('idx_auto_sync', 'auto_sync'),
        Index('idx_updated_at', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<SyncConfig(id={self.id}, platform={self.platform}, document_id={self.document_id})>"