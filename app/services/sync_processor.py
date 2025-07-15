"""
Sync task processor - handles the actual synchronization between platforms
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.utils.helpers import get_beijing_time

from app.services import FeishuClient, NotionClient, QiniuClient
from app.models import SyncRecordService, ImageMappingService

logger = logging.getLogger(__name__)


class SyncProcessor:
    """同步任务处理器"""
    
    def __init__(self):
        self.feishu_client = FeishuClient()
        self.notion_client = NotionClient()
        self.qiniu_client = QiniuClient()
    
    def process_sync_task(self, sync_record_id: int) -> Dict[str, Any]:
        """
        处理同步任务
        
        Args:
            sync_record_id: 同步记录ID
            
        Returns:
            同步结果
        """
        try:
            # 使用数据库会话直接获取同步记录
            from database.connection import db
            from database.models import SyncRecord
            with db.get_session() as session:
                sync_record = session.query(SyncRecord).filter(
                    SyncRecord.id == sync_record_id
                ).first()
                
                if not sync_record:
                    raise Exception(f"Sync record {sync_record_id} not found")
                
                # 提取数据
                record_data = {
                    'id': sync_record.id,
                    'source_platform': sync_record.source_platform,
                    'target_platform': sync_record.target_platform,
                    'source_id': sync_record.source_id,
                    'target_id': sync_record.target_id,
                    'content_type': sync_record.content_type,
                    'sync_status': sync_record.sync_status
                }
                
                logger.info(f"Processing sync task {sync_record_id}: {record_data['source_platform']} -> {record_data['target_platform']}")
                
                # 更新状态为处理中
                sync_record.sync_status = 'processing'
                sync_record.last_sync_time = get_beijing_time().replace(tzinfo=None)
                sync_record.updated_at = get_beijing_time().replace(tzinfo=None)
                session.commit()
            
            # 根据同步方向选择处理方法
            if record_data['source_platform'] == 'feishu' and record_data['target_platform'] == 'notion':
                result = self._sync_feishu_to_notion_by_data(record_data)
            elif record_data['source_platform'] == 'notion' and record_data['target_platform'] == 'feishu':
                result = self._sync_notion_to_feishu_by_data(record_data)
            else:
                raise Exception(f"Unsupported sync direction: {record_data['source_platform']} -> {record_data['target_platform']}")
            
            # 更新同步记录为成功
            with db.get_session() as session:
                sync_record = session.query(SyncRecord).filter(SyncRecord.id == sync_record_id).first()
                if sync_record:
                    sync_record.sync_status = 'success'
                    sync_record.target_id = result.get('target_id')
                    sync_record.last_sync_time = get_beijing_time().replace(tzinfo=None)
                    sync_record.updated_at = get_beijing_time().replace(tzinfo=None)
                    session.commit()
            
            logger.info(f"Successfully completed sync task {sync_record_id}")
            return {
                "success": True,
                "sync_record_id": sync_record_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error processing sync task {sync_record_id}: {e}")
            
            # 更新同步记录为失败
            try:
                with db.get_session() as session:
                    sync_record = session.query(SyncRecord).filter(SyncRecord.id == sync_record_id).first()
                    if sync_record:
                        sync_record.sync_status = 'failed'
                        sync_record.error_message = str(e)
                        sync_record.last_sync_time = get_beijing_time().replace(tzinfo=None)
                        sync_record.updated_at = get_beijing_time().replace(tzinfo=None)
                        session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update sync record {sync_record_id} status: {update_error}")
            
            return {
                "success": False,
                "sync_record_id": sync_record_id,
                "error": str(e)
            }
    
    def _sync_feishu_to_notion(self, sync_record) -> Dict[str, Any]:
        """飞书到Notion的同步"""
        try:
            # 1. 从飞书获取文档内容
            try:
                feishu_content = self.feishu_client.parse_document_content(sync_record.source_id)
                logger.info(f"Retrieved Feishu document: {feishu_content['title']}")
            except Exception as e:
                # 不再返回测试数据，而是抛出详细错误
                error_msg = f"获取飞书文档失败 (文档ID: {sync_record.source_id}): {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # 2. 处理图片
            image_mappings = {}
            if feishu_content.get('images'):
                logger.info(f"Processing {len(feishu_content['images'])} images")
                image_mappings = self.qiniu_client.process_feishu_images(
                    self.feishu_client, 
                    feishu_content['images']
                )
                
                # 保存图片映射到数据库
                for file_token, mapping in image_mappings.items():
                    if mapping.get('cdn_url') and not mapping.get('error'):
                        ImageMappingService.create_image_mapping(
                            original_url=f"feishu://{file_token}",
                            qiniu_url=mapping['cdn_url'],
                            file_hash=mapping.get('file_hash', ''),
                            file_size=mapping.get('file_size', 0)
                        )
            
            # 3. 更新Notion块中的图片链接
            self._replace_image_placeholders(feishu_content, image_mappings)
            
            # 4. 检查目标页面是否存在
            target_page_id = sync_record.target_id
            
            if target_page_id:
                # 更新现有页面
                try:
                    result = self.notion_client.update_page_from_feishu(target_page_id, feishu_content)
                    logger.info(f"Updated existing Notion page: {target_page_id}")
                    return {
                        "action": "update",
                        "target_id": target_page_id,
                        "title": feishu_content['title'],
                        "images_processed": len(image_mappings)
                    }
                except Exception as e:
                    logger.warning(f"Failed to update existing page {target_page_id}: {e}")
                    # 如果更新失败，尝试创建新页面
                    target_page_id = None
            
            if not target_page_id:
                # 创建新页面 - 在数据库中创建
                database_id = self._get_default_notion_parent()
                
                # 为数据库页面创建属性
                properties = {
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": feishu_content['title']
                                }
                            }
                        ]
                    },
                    "type": {
                        "select": {
                            "name": "Post"
                        }
                    },
                    "status": {
                        "select": {
                            "name": "Published"
                        }
                    },
                    "category": {
                        "select": {
                            "name": notion_category or "技术分享"
                        }
                    },
                    "date": {
                        "date": {
                            "start": get_beijing_time().date().isoformat()
                        }
                    }
                }
                
                # 转换内容块
                content_blocks = self.notion_client.convert_feishu_to_notion_blocks(feishu_content)
                
                # 在数据库中创建页面
                page_data = self.notion_client.create_database_page(database_id, properties, content_blocks)
                target_page_id = page_data['id']
                
                logger.info(f"Created new Notion database page: {target_page_id}")
                return {
                    "action": "create",
                    "target_id": target_page_id,
                    "title": feishu_content['title'],
                    "images_processed": len(image_mappings)
                }
            
        except Exception as e:
            logger.error(f"Error in Feishu to Notion sync: {e}")
            raise
    
    def _sync_feishu_to_notion_by_data(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """飞书到Notion的同步（使用数据字典）"""
        # 从配置中获取Notion分类
        notion_category = self._get_notion_category_for_document(record_data['source_id'])
        return self._sync_feishu_to_notion_impl(record_data['source_id'], record_data.get('target_id'), notion_category)
    
    def _sync_notion_to_feishu_by_data(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notion到飞书的同步（使用数据字典）"""
        return self._sync_notion_to_feishu_impl(record_data['source_id'], record_data.get('target_id'))
    
    def _sync_feishu_to_notion_impl(self, source_id: str, target_id: Optional[str] = None, notion_category: Optional[str] = None) -> Dict[str, Any]:
        """飞书到Notion同步的实际实现"""
        try:
            # 1. 从飞书获取文档内容
            try:
                feishu_content = self.feishu_client.parse_document_content(source_id)
                document_title = feishu_content.get('title', '')
                logger.info(f"Retrieved Feishu document: {document_title}")
                
                # 更新同步记录的文档标题
                from database.connection import db
                from database.models import SyncRecord
                with db.get_session() as session:
                    sync_record = session.query(SyncRecord).filter(
                        SyncRecord.source_platform == 'feishu',
                        SyncRecord.source_id == source_id
                    ).order_by(SyncRecord.created_at.desc()).first()
                    
                    if sync_record and not sync_record.document_title:
                        sync_record.document_title = document_title
                        session.commit()
                        logger.info(f"Updated document title for record {sync_record.id}: {document_title}")
                        
            except Exception as e:
                # 不再返回测试数据，而是抛出详细错误
                error_msg = f"获取飞书文档失败 (文档ID: {source_id}): {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # 2. 处理图片
            image_mappings = {}
            if feishu_content.get('images'):
                logger.info(f"Processing {len(feishu_content['images'])} images")
                image_mappings = self.qiniu_client.process_feishu_images(
                    self.feishu_client, 
                    feishu_content['images']
                )
                
                # 保存图片映射到数据库
                for file_token, mapping in image_mappings.items():
                    if mapping.get('cdn_url') and not mapping.get('error'):
                        ImageMappingService.create_image_mapping(
                            original_url=f"feishu://{file_token}",
                            qiniu_url=mapping['cdn_url'],
                            file_hash=mapping.get('file_hash', ''),
                            file_size=mapping.get('file_size', 0)
                        )
            
            # 3. 更新Notion块中的图片链接
            self._replace_image_placeholders(feishu_content, image_mappings)
            
            # 4. 检查目标页面是否存在
            target_page_id = target_id
            
            if target_page_id:
                # 更新现有页面
                try:
                    result = self.notion_client.update_page_from_feishu(target_page_id, feishu_content)
                    logger.info(f"Updated existing Notion page: {target_page_id}")
                    return {
                        "action": "update",
                        "target_id": target_page_id,
                        "title": feishu_content['title'],
                        "images_processed": len(image_mappings)
                    }
                except Exception as e:
                    logger.warning(f"Failed to update existing page {target_page_id}: {e}")
                    # 如果更新失败，尝试创建新页面
                    target_page_id = None
            
            if not target_page_id:
                # 先检查数据库中是否已存在同标题的页面
                database_id = self._get_default_notion_parent()
                existing_page = self.notion_client.find_page_in_database_by_title(database_id, feishu_content['title'])
                
                if existing_page:
                    # 如果存在同标题页面，更新现有页面而不是创建新页面
                    existing_page_id = existing_page['id']
                    logger.info(f"Found existing page with title '{feishu_content['title']}', updating instead of creating new page: {existing_page_id}")
                    
                    try:
                        result = self.notion_client.update_page_from_feishu(existing_page_id, feishu_content)
                        
                        # 更新同步记录的target_id，避免下次重复创建
                        with db.get_session() as session:
                            current_record = session.query(SyncRecord).filter(
                                SyncRecord.source_platform == 'feishu',
                                SyncRecord.source_id == source_id
                            ).order_by(SyncRecord.created_at.desc()).first()
                            
                            if current_record and not current_record.target_id:
                                current_record.target_id = existing_page_id
                                current_record.updated_at = get_beijing_time().replace(tzinfo=None)
                                session.commit()
                                logger.info(f"Updated sync record {current_record.id} with target_id: {existing_page_id}")
                        
                        return {
                            "action": "update_existing",
                            "target_id": existing_page_id,
                            "title": feishu_content['title'],
                            "images_processed": len(image_mappings)
                        }
                    except Exception as e:
                        logger.warning(f"Failed to update existing page {existing_page_id}: {e}")
                        # 如果更新失败，继续创建新页面（但记录警告）
                
                # 创建新页面 - 在数据库中创建
                # 为数据库页面创建属性（安全版本）
                try:
                    # 先获取数据库的属性schema
                    database_info = self.notion_client.get_database_properties(database_id)
                    available_properties = database_info.get('properties', {})
                    logger.info(f"Database properties: {list(available_properties.keys())}")
                    
                    # 基础属性
                    properties = {}
                    
                    # 查找标题属性
                    title_prop = None
                    for prop_name, prop_info in available_properties.items():
                        if prop_info.get('type') == 'title':
                            title_prop = prop_name
                            break
                    
                    if title_prop:
                        properties[title_prop] = {
                            "title": [
                                {
                                    "text": {
                                        "content": feishu_content['title']
                                    }
                                }
                            ]
                        }
                    
                    # 安全地添加其他属性（只有当数据库中存在时才添加）
                    if "type" in available_properties and available_properties["type"].get("type") == "select":
                        properties["type"] = {
                            "select": {
                                "name": "Post"
                            }
                        }
                    
                    if "status" in available_properties and available_properties["status"].get("type") == "select":
                        properties["status"] = {
                            "select": {
                                "name": "Published"
                            }
                        }
                    
                    if "category" in available_properties and available_properties["category"].get("type") == "select":
                        properties["category"] = {
                            "select": {
                                "name": notion_category or "技术分享"
                            }
                        }
                    
                    if "date" in available_properties and available_properties["date"].get("type") == "date":
                        properties["date"] = {
                            "date": {
                                "start": get_beijing_time().date().isoformat()
                            }
                        }
                    
                    logger.info(f"Creating page with properties: {list(properties.keys())}")
                    
                except Exception as e:
                    logger.warning(f"Failed to get database properties, using minimal properties: {e}")
                    # 如果获取数据库属性失败，使用最简单的属性
                    properties = {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": feishu_content['title']
                                    }
                                }
                            ]
                        }
                    }
                
                # 转换内容块
                content_blocks = self.notion_client.convert_feishu_to_notion_blocks(feishu_content)
                
                # Notion API限制：单次请求最多100个子块
                MAX_BLOCKS_PER_REQUEST = 100
                
                if len(content_blocks) <= MAX_BLOCKS_PER_REQUEST:
                    # 内容块数量在限制范围内，直接创建页面
                    page_data = self.notion_client.create_database_page(database_id, properties, content_blocks)
                    target_page_id = page_data['id']
                    logger.info(f"Created new Notion database page with {len(content_blocks)} blocks: {target_page_id}")
                else:
                    # 内容块数量超过限制，分批处理
                    logger.info(f"Content has {len(content_blocks)} blocks, exceeding Notion API limit of {MAX_BLOCKS_PER_REQUEST}. Using batch processing.")
                    
                    # 先创建页面，只包含前100个块
                    initial_blocks = content_blocks[:MAX_BLOCKS_PER_REQUEST]
                    page_data = self.notion_client.create_database_page(database_id, properties, initial_blocks)
                    target_page_id = page_data['id']
                    logger.info(f"Created new Notion database page with initial {len(initial_blocks)} blocks: {target_page_id}")
                    
                    # 分批添加剩余的内容块
                    remaining_blocks = content_blocks[MAX_BLOCKS_PER_REQUEST:]
                    batch_size = MAX_BLOCKS_PER_REQUEST
                    
                    for i in range(0, len(remaining_blocks), batch_size):
                        batch = remaining_blocks[i:i + batch_size]
                        try:
                            self.notion_client.append_blocks(target_page_id, batch)
                            logger.info(f"Appended batch of {len(batch)} blocks to page {target_page_id}")
                        except Exception as e:
                            logger.error(f"Failed to append batch {i//batch_size + 1} to page {target_page_id}: {e}")
                            # 记录错误但继续处理其他批次
                    
                    logger.info(f"Completed batch processing for page {target_page_id}. Total blocks: {len(content_blocks)}")
                
                logger.info(f"Created new Notion database page: {target_page_id}")
                return {
                    "action": "create",
                    "target_id": target_page_id,
                    "title": feishu_content['title'],
                    "images_processed": len(image_mappings)
                }
            
        except Exception as e:
            logger.error(f"Error in Feishu to Notion sync: {e}")
            raise
    
    def _sync_notion_to_feishu_impl(self, source_id: str, target_id: Optional[str] = None) -> Dict[str, Any]:
        """Notion到飞书同步的实际实现"""
        try:
            # 获取Notion页面内容
            page_data = self.notion_client.get_page(source_id)
            page_content = self.notion_client.get_page_content(source_id)
            
            logger.info(f"Retrieved Notion page with {len(page_content)} blocks")
            
            # 注意：飞书API对文档创建和更新有严格限制
            # 这里只是一个基础实现，实际项目中需要更复杂的处理
            
            return {
                "action": "placeholder",
                "target_id": None,
                "title": page_data.get('properties', {}).get('title', {}).get('title', [{}])[0].get('text', {}).get('content', 'Untitled'),
                "blocks_processed": len(page_content),
                "note": "Notion to Feishu sync requires manual implementation due to API limitations"
            }
            
        except Exception as e:
            logger.error(f"Error in Notion to Feishu sync: {e}")
            raise
    
    def _sync_notion_to_feishu(self, sync_record) -> Dict[str, Any]:
        """Notion到飞书的同步（基础实现）"""
        try:
            # 获取Notion页面内容
            page_data = self.notion_client.get_page(sync_record.source_id)
            page_content = self.notion_client.get_page_content(sync_record.source_id)
            
            logger.info(f"Retrieved Notion page with {len(page_content)} blocks")
            
            # 注意：飞书API对文档创建和更新有严格限制
            # 这里只是一个基础实现，实际项目中需要更复杂的处理
            
            return {
                "action": "placeholder",
                "target_id": None,
                "title": page_data.get('properties', {}).get('title', {}).get('title', [{}])[0].get('text', {}).get('content', 'Untitled'),
                "blocks_processed": len(page_content),
                "note": "Notion to Feishu sync requires manual implementation due to API limitations"
            }
            
        except Exception as e:
            logger.error(f"Error in Notion to Feishu sync: {e}")
            raise
    
    def _replace_image_placeholders(self, content: Dict[str, Any], image_mappings: Dict[str, Any]):
        """替换内容中的图片占位符"""
        try:
            blocks = content.get('blocks', [])
            
            for block in blocks:
                if block.get('type') == 'image':
                    file_token = block.get('file_token')
                    if file_token and file_token in image_mappings:
                        mapping = image_mappings[file_token]
                        if mapping.get('cdn_url'):
                            # 更新图片块为实际的CDN链接
                            block['cdn_url'] = mapping['cdn_url']
                            block['processed'] = True
                            logger.info(f"Replaced image placeholder {file_token} with {mapping['cdn_url']}")
            
        except Exception as e:
            logger.error(f"Error replacing image placeholders: {e}")
    
    def _get_default_notion_parent(self) -> str:
        """获取默认的Notion父页面ID"""
        from config import settings
        parent_id = settings.notion_test_page_id
        logger.info(f"Using Notion parent/database ID: {parent_id}")
        return parent_id
    
    def validate_sync_requirements(self, sync_record) -> bool:
        """验证同步要求"""
        try:
            # 检查源文档是否存在
            if sync_record.source_platform == 'feishu':
                try:
                    doc_info = self.feishu_client.get_document_info(sync_record.source_id)
                    if doc_info is None:
                        logger.warning(f"Source Feishu document {sync_record.source_id} not accessible or not found")
                        return False
                except Exception as e:
                    logger.error(f"Source Feishu document {sync_record.source_id} not accessible: {e}")
                    return False
            
            elif sync_record.source_platform == 'notion':
                try:
                    self.notion_client.get_page(sync_record.source_id)
                except Exception as e:
                    logger.error(f"Source Notion page {sync_record.source_id} not accessible: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating sync requirements: {e}")
            return False
    
    def get_sync_preview(self, source_platform: str, source_id: str) -> Dict[str, Any]:
        """获取同步预览信息"""
        try:
            if source_platform == 'feishu':
                content = self.feishu_client.parse_document_content(source_id)
                return {
                    "title": content['title'],
                    "blocks_count": len(content['blocks']),
                    "images_count": len(content['images']),
                    "size_estimate": len(str(content)),
                    "metadata": content['metadata']
                }
            
            elif source_platform == 'notion':
                page_data = self.notion_client.get_page(source_id)
                page_content = self.notion_client.get_page_content(source_id)
                
                return {
                    "title": page_data.get('properties', {}).get('title', {}).get('title', [{}])[0].get('text', {}).get('content', 'Untitled'),
                    "blocks_count": len(page_content),
                    "images_count": 0,  # 需要进一步解析
                    "size_estimate": len(str(page_content)),
                    "created_time": page_data.get('created_time'),
                    "last_edited_time": page_data.get('last_edited_time')
                }
            
            else:
                raise Exception(f"Unsupported platform: {source_platform}")
                
        except Exception as e:
            logger.error(f"Error getting sync preview: {e}")
            raise
    
    def _get_notion_category_for_document(self, document_id: str) -> Optional[str]:
        """根据文档ID获取配置的Notion分类"""
        try:
            from database.connection import db
            from database.models import SyncConfig
            
            with db.get_session() as session:
                # 查找对应的同步配置
                config = session.query(SyncConfig).filter(
                    SyncConfig.platform == 'feishu',
                    SyncConfig.document_id == document_id
                ).first()
                
                if config and config.notion_category:
                    return config.notion_category
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting notion category for document {document_id}: {e}")
            return None