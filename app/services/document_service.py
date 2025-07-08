#!/usr/bin/env python3
"""
文档服务层 - 处理文档解析、验证和批量操作相关的业务逻辑（SQLAlchemy版本）
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from .sync_service import SyncService
from database.connection import db
from database.models import SyncRecord


class DocumentService(SyncService):
    """文档服务类 - 继承同步服务的基础功能，专门处理文档相关操作"""
    
    def __init__(self, logger: logging.Logger = None):
        super().__init__(logger)
    
    def parse_document_urls(self, urls: List[str]) -> Dict[str, Any]:
        """解析文档URL获取信息"""
        try:
            if not urls:
                raise ValueError("请提供要解析的URL")
            
            document_ids = []
            parsed_results = []
            
            for url in urls:
                try:
                    # 简单的URL解析逻辑
                    if 'feishu' in url or 'larksuite' in url:
                        platform = 'feishu'
                        # 提取文档ID（简化版）
                        if '/docs/' in url:
                            doc_id = url.split('/docs/')[-1].split('?')[0].split('#')[0]
                        elif '/docx/' in url:
                            doc_id = url.split('/docx/')[-1].split('?')[0].split('#')[0]
                        else:
                            doc_id = url.split('/')[-1].split('?')[0].split('#')[0] if '/' in url else url
                    elif 'notion' in url:
                        platform = 'notion'
                        doc_id = url.split('/')[-1].split('?')[0].split('#')[0] if '/' in url else url
                    else:
                        # 如果不是链接，可能是直接的文档ID
                        if not url.startswith('http'):
                            platform = 'feishu'  # 默认平台
                            doc_id = url
                        else:
                            continue  # 跳过不支持的URL
                    
                    # 清理文档ID
                    doc_id = doc_id.strip()
                    if doc_id:
                        document_ids.append(doc_id)
                        parsed_results.append({
                            'url': url,
                            'platform': platform,
                            'document_id': doc_id,
                            'status': 'parsed'
                        })
                
                except Exception as e:
                    parsed_results.append({
                        'url': url,
                        'platform': 'unknown',
                        'document_id': None,
                        'status': 'error',
                        'error_message': str(e)
                    })
            
            return {
                'total_urls': len(urls),
                'parsed_count': len(document_ids),
                'document_ids': document_ids,
                'results': parsed_results
            }
            
        except Exception as e:
            self.logger.error(f"解析文档URL失败: {e}")
            raise
    
    def create_manual_sync_tasks(self, document_ids: List[str], source_platform: str = 'feishu', 
                                target_platform: str = 'notion', force_resync: bool = False, 
                                notion_category: str = None, notion_type: str = None) -> Dict[str, Any]:
        """创建手动同步任务（立即执行）"""
        try:
            if not document_ids:
                raise ValueError("请提供要同步的文档ID")
            
            if not source_platform or not target_platform:
                raise ValueError("请提供源平台和目标平台")
            
            # 验证平台类型
            valid_platforms = ['feishu', 'notion']
            if source_platform not in valid_platforms or target_platform not in valid_platforms:
                raise ValueError("无效的平台类型")
            
            created_records = []
            record_ids = []
            
            # 使用更强的并发控制策略防止重复记录
            import time
            import random
            from datetime import datetime, timedelta
            
            for doc_id in document_ids:
                # 添加随机延迟避免完全同时的请求
                time.sleep(random.uniform(0.01, 0.05))
                
                # 重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        with db.get_session() as session:
                            # 检查最近10秒内是否已有同样的同步记录
                            cutoff_time = datetime.now() - timedelta(seconds=10)
                            existing_record = session.query(SyncRecord).filter(
                                SyncRecord.source_platform == source_platform,
                                SyncRecord.target_platform == target_platform,
                                SyncRecord.source_id == doc_id,
                                SyncRecord.sync_status.in_(['pending', 'processing']),
                                SyncRecord.created_at >= cutoff_time
                            ).first()
                            
                            if existing_record and not force_resync:
                                self.logger.info(f"文档 {doc_id} 在最近10秒内已有同步任务: {existing_record.record_number}")
                                record_ids.append(existing_record.id)
                                created_records.append({
                                    "record_number": existing_record.record_number,
                                    "document_id": doc_id,
                                    "record_id": existing_record.id,
                                    "status": "existing"
                                })
                                break  # 跳出重试循环
                            
                            record_number = self.generate_record_number()
                            
                            # 创建同步记录
                            new_record = SyncRecord(
                                record_number=record_number,
                                source_platform=source_platform,
                                target_platform=target_platform,
                                source_id=doc_id,
                                sync_status='processing'
                            )
                            
                            session.add(new_record)
                            session.commit()
                            
                            # 创建成功后再次检查是否有重复（双重检查）
                            time.sleep(0.1)  # 短暂等待其他可能的并发请求
                            duplicate_records = session.query(SyncRecord).filter(
                                SyncRecord.source_platform == source_platform,
                                SyncRecord.target_platform == target_platform,
                                SyncRecord.source_id == doc_id,
                                SyncRecord.sync_status == 'processing',
                                SyncRecord.created_at >= cutoff_time
                            ).order_by(SyncRecord.created_at).all()
                            
                            if len(duplicate_records) > 1:
                                # 如果有重复，保留最早的，删除后创建的
                                records_to_delete = duplicate_records[1:]
                                for dup_record in records_to_delete:
                                    if dup_record.id == new_record.id:
                                        # 当前创建的记录是重复的，删除它并使用最早的记录
                                        session.delete(new_record)
                                        session.commit()
                                        earliest_record = duplicate_records[0]
                                        self.logger.warning(f"删除重复记录 {new_record.record_number}，使用已存在记录 {earliest_record.record_number}")
                                        record_ids.append(earliest_record.id)
                                        created_records.append({
                                            "record_number": earliest_record.record_number,
                                            "document_id": doc_id,
                                            "record_id": earliest_record.id,
                                            "status": "existing"
                                        })
                                        break
                            else:
                                # 没有重复，使用新创建的记录
                                record_id = new_record.id
                                record_ids.append(record_id)
                                created_records.append({
                                    "record_number": record_number,
                                    "document_id": doc_id,
                                    "record_id": record_id,
                                    "status": "created"
                                })
                            break  # 成功，跳出重试循环
                            
                    except Exception as e:
                        if attempt < max_retries - 1:
                            self.logger.warning(f"文档 {doc_id} 第 {attempt + 1} 次尝试失败: {e}，等待重试...")
                            time.sleep(random.uniform(0.1, 0.3))
                            continue
                        else:
                            self.logger.error(f"文档 {doc_id} 所有重试都失败: {e}")
                            raise e
            
            # 立即触发同步处理
            successful_syncs = 0
            failed_syncs = 0
            
            for i, record_id in enumerate(record_ids):
                try:
                    # 调用同步处理器
                    self._execute_sync_immediately(record_id, source_platform, target_platform, document_ids[i], notion_category, notion_type)
                    successful_syncs += 1
                except Exception as sync_error:
                    self.logger.error(f"同步记录 {record_id} 执行失败: {sync_error}")
                    failed_syncs += 1
                    # 更新记录状态为失败
                    self._update_sync_status(record_id, 'failed', str(sync_error))
            
            # 统计创建和现有记录
            new_records_count = len([r for r in created_records if r.get('status') != 'existing'])
            existing_records_count = len([r for r in created_records if r.get('status') == 'existing'])
            
            message_parts = []
            if new_records_count > 0:
                message_parts.append(f"创建 {new_records_count} 个新任务")
            if existing_records_count > 0:
                message_parts.append(f"跳过 {existing_records_count} 个已存在任务")
            
            message = f"处理完成：{', '.join(message_parts)}（成功: {successful_syncs}, 失败: {failed_syncs}）"
            
            return {
                "message": message,
                "created_records": created_records,
                "total_processed": len(created_records),
                "new_records": new_records_count,
                "existing_records": existing_records_count,
                "successful_syncs": successful_syncs,
                "failed_syncs": failed_syncs
            }
            
        except Exception as e:
            self.logger.error(f"创建手动同步任务失败: {e}")
            raise
    
    def _execute_sync_immediately(self, record_id: int, source_platform: str, target_platform: str, document_id: str, notion_category: str = None, notion_type: str = None):
        """立即执行同步任务"""
        try:
            if source_platform == 'feishu' and target_platform == 'notion':
                result = self._sync_feishu_to_notion(document_id, record_id, notion_category, notion_type)
            elif source_platform == 'notion' and target_platform == 'feishu':
                result = self._sync_notion_to_feishu(document_id, record_id)
            else:
                raise ValueError(f"不支持的同步方向: {source_platform} -> {target_platform}")
            
            if result.get('success'):
                self._update_sync_status(record_id, 'completed', result.get('message'))
                if result.get('target_id'):
                    self._update_target_id(record_id, result['target_id'])
            else:
                self._update_sync_status(record_id, 'failed', result.get('message'))
                
        except Exception as e:
            self.logger.error(f"执行同步任务失败: {e}")
            raise
    
    def _sync_feishu_to_notion(self, feishu_doc_id: str, record_id: int, notion_category: str = None, notion_type: str = None) -> Dict[str, Any]:
        """将飞书文档同步到Notion"""
        try:
            # 导入客户端
            from app.services.feishu_client import FeishuClient
            from app.services.notion_client import NotionClient
            
            feishu_client = FeishuClient(logger=self.logger)
            notion_client = NotionClient()
            
            # 1. 从飞书获取文档内容
            self.logger.info(f"正在从飞书获取文档内容: {feishu_doc_id}")
            
            # 如果是测试文档ID，使用模拟数据
            if feishu_doc_id.startswith("test_"):
                self.logger.info("使用测试模拟数据进行同步")
                feishu_content = {
                    "title": f"测试文档 - {feishu_doc_id}",
                    "content": [
                        {
                            "type": "paragraph",
                            "text": f"这是一个测试同步文档，文档ID: {feishu_doc_id}"
                        },
                        {
                            "type": "paragraph", 
                            "text": "测试内容：手动同步功能正常工作！"
                        }
                    ],
                    "document_id": feishu_doc_id
                }
            else:
                feishu_content = feishu_client.parse_document_content(feishu_doc_id)
                
                if not feishu_content:
                    raise Exception("无法获取飞书文档内容")
            
            # 2. 使用配置的固定Notion数据库进行同步
            from config.settings import settings
            target_notion_id = settings.notion_test_page_id or settings.notion_database_id
            
            if not target_notion_id:
                raise Exception("未配置目标Notion数据库ID，请检查NOTION_TEST_PAGE_ID或NOTION_DATABASE_ID环境变量")
            
            # 转换Notion ID格式（如果需要）
            if len(target_notion_id) == 32 and "-" not in target_notion_id:
                # 将32位字符ID转换为带连字符的格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
                target_notion_id = f"{target_notion_id[:8]}-{target_notion_id[8:12]}-{target_notion_id[12:16]}-{target_notion_id[16:20]}-{target_notion_id[20:]}"
                self.logger.info(f"转换数据库ID格式: {target_notion_id}")
            
            # 3. 检查Notion数据库中是否已存在同标题页面
            title = feishu_content.get('title', f'同步文档 - {feishu_doc_id}')
            
            # 先查找是否存在同标题的页面
            existing_page = notion_client.find_page_in_database_by_title(target_notion_id, title)
            
            if existing_page:
                existing_page_id = existing_page['id']
                self.logger.info(f"发现已存在同标题页面，更新现有页面: {existing_page_id}")
                
                # 更新现有页面而不是创建新页面
                content_blocks = []
            else:
                # 创建新页面
                self.logger.info(f"在Notion数据库中创建新页面: {target_notion_id}")
                content_blocks = []
            
            # Convert feishu content to Notion blocks
            document_title = feishu_content.get('title', '')
            for block in feishu_content.get('blocks', []):
                block_type = block.get('type')
                block_content = block.get('content', '')
                
                # 跳过空内容的块
                if not block_content and block_type not in ['image']:
                    continue
                
                # 跳过与文档标题重复的heading1块，避免重复标题
                if block_type == 'heading1' and block_content and block_content.strip() == document_title.strip():
                    continue
                
                if block_type in ['text']:
                    content_blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": block_content
                                }
                            }]
                        }
                    })
                elif block_type in ['heading1', 'heading2', 'heading3']:
                    # 处理标题块
                    heading_level = block.get('level', 1)
                    heading_type = f"heading_{min(heading_level, 3)}"  # Notion最多支持3级标题
                    content_blocks.append({
                        "object": "block",
                        "type": heading_type,
                        heading_type: {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": block_content
                                }
                            }]
                        }
                    })
                elif block_type == 'code':
                    # 处理代码块
                    language = block.get('language', 'plain_text')
                    # 如果内容为空，添加占位符
                    code_content = block_content if block_content else "# 代码内容"
                    content_blocks.append({
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": code_content
                                }
                            }],
                            "language": language
                        }
                    })
                elif block_type == 'image':
                    # 处理图片块，先上传到七牛云再创建Notion图片块
                    file_token = block.get('file_token', '')
                    alt_text = block.get('alt_text', '')
                    if file_token:
                        try:
                            # 导入七牛云客户端
                            from app.services.qiniu_client import QiniuClient
                            qiniu_client = QiniuClient()
                            
                            # 上传图片到七牛云
                            cdn_url, file_hash, file_size = qiniu_client.download_from_feishu_and_upload(
                                feishu_client, file_token
                            )
                            
                            # 创建真正的Notion图片块
                            content_blocks.append({
                                "object": "block",
                                "type": "image",
                                "image": {
                                    "type": "external",
                                    "external": {
                                        "url": cdn_url
                                    },
                                    "caption": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": alt_text or "图片"
                                            }
                                        }
                                    ] if alt_text else []
                                }
                            })
                            
                            self.logger.info(f"成功处理图片: {file_token} -> {cdn_url}")
                            
                        except Exception as e:
                            self.logger.error(f"图片处理失败 {file_token}: {e}")
                            # 如果图片处理失败，创建占位符
                            content_blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{
                                        "type": "text",
                                        "text": {
                                            "content": f"🖼️ 图片处理失败 ({alt_text})\n错误: {str(e)}"
                                        }
                                    }]
                                }
                            })
                else:
                    # 其他类型都当作段落处理
                    content_blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": block_content or f"[{block_type}内容]"
                                }
                            }]
                        }
                    })
            
            # 注释掉源文档时间戳和来源信息，保持文档内容干净
            # 如果需要显示来源信息，可以在这里重新启用
            # from datetime import datetime
            # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # content_blocks.append({
            #     "object": "block",
            #     "type": "paragraph", 
            #     "paragraph": {
            #         "rich_text": [{
            #             "type": "text",
            #             "text": {
            #                 "content": f"同步时间: {timestamp} | 来源: 飞书文档 {feishu_doc_id}"
            #             },
            #             "annotations": {
            #                 "italic": True,
            #                 "color": "gray"
            #             }
            #         }]
            #     }
            # })
            
            if existing_page:
                # 更新现有页面
                try:
                    update_result = notion_client.update_page_from_feishu(existing_page_id, feishu_content)
                    self.logger.info(f"成功更新现有Notion页面: {existing_page_id}")
                    
                    # 更新同步记录的target_id
                    from database.connection import db
                    from database.models import SyncRecord
                    with db.get_session() as session:
                        sync_record = session.query(SyncRecord).filter(SyncRecord.id == record_id).first()
                        if sync_record:
                            sync_record.target_id = existing_page_id
                            sync_record.updated_at = datetime.now()
                            session.commit()
                    
                    return {
                        'success': True,
                        'message': f"成功更新飞书文档 {feishu_doc_id} 到现有Notion页面",
                        'target_id': existing_page_id,
                        'action': 'updated'
                    }
                except Exception as e:
                    self.logger.warning(f"更新现有页面失败: {e}, 将创建新页面")
                    # 如果更新失败，继续创建新页面
            
            # 创建新页面
            self.logger.info(f"在数据库 {target_notion_id} 中创建新页面，标题: {title}")
            
            # 为数据库页面创建属性
            properties = {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "type": {
                    "select": {
                        "name": notion_type or "Post"
                    }
                },
                "status": {
                    "select": {
                        "name": "Draft"
                    }
                },
                "category": {
                    "select": {
                        "name": notion_category or "技术分享"
                    }
                },
                "date": {
                    "date": {
                        "start": datetime.now().date().isoformat()
                    }
                }
            }
            
            # 创建页面
            notion_result = notion_client.create_database_page(target_notion_id, properties, content_blocks)
            notion_result['action'] = 'created'
            
            if notion_result.get('id'):
                target_notion_id = notion_result['id']
                notion_result['success'] = True
                notion_result['page_id'] = target_notion_id
            else:
                notion_result['success'] = False
            
            if not notion_result.get('success'):
                raise Exception(f"Notion操作失败: {notion_result.get('error')}")
            
            self.logger.info(f"成功同步到Notion页面: {target_notion_id}")
            
            return {
                'success': True,
                'message': f"成功同步飞书文档 {feishu_doc_id} 到 Notion",
                'target_id': target_notion_id
            }
            
        except Exception as e:
            self.logger.error(f"飞书到Notion同步失败: {e}")
            raise
    
    def _sync_notion_to_feishu(self, notion_page_id: str, record_id: int) -> Dict[str, Any]:
        """将Notion页面同步到飞书（暂未实现）"""
        try:
            # 这是一个占位符实现
            self.logger.info(f"Notion到飞书的同步暂未完全实现: {notion_page_id}")
            return {
                'success': True,
                'message': f"Notion页面 {notion_page_id} 同步请求已记录（功能开发中）",
                'target_id': None
            }
            
        except Exception as e:
            self.logger.error(f"Notion到飞书同步失败: {e}")
            raise
    
    def _update_sync_status(self, record_id: int, status: str, message: str = None):
        """更新同步记录状态"""
        try:
            with db.get_session() as session:
                record = session.query(SyncRecord).filter(SyncRecord.id == record_id).first()
                if record:
                    record.sync_status = status
                    if message:
                        record.error_message = message
                    session.commit()
        except Exception as e:
            self.logger.error(f"更新同步状态失败: {e}")
    
    def _update_target_id(self, record_id: int, target_id: str):
        """更新目标ID"""
        try:
            with db.get_session() as session:
                record = session.query(SyncRecord).filter(SyncRecord.id == record_id).first()
                if record:
                    record.target_id = target_id
                    session.commit()
        except Exception as e:
            self.logger.error(f"更新目标ID失败: {e}")
    
    def trigger_single_sync(self, document_id: str, source_platform: str = 'feishu', 
                           target_platform: str = 'notion') -> Dict[str, Any]:
        """触发单个文档同步"""
        try:
            if not document_id:
                raise ValueError("请提供文档ID")
            
            # 创建同步记录
            record_number = self.generate_record_number()
            
            with db.get_session() as session:
                new_record = SyncRecord(
                    record_number=record_number,
                    source_platform=source_platform,
                    target_platform=target_platform,
                    source_id=document_id,
                    sync_status='pending'
                )
                
                session.add(new_record)
                session.commit()
                
                record_id = new_record.id
            
            self.logger.info(f"已创建同步任务: {record_number}")
            
            return {
                'success': True,
                'message': f"同步任务已创建: {record_number}",
                'record_id': record_id,
                'record_number': record_number
            }
            
        except Exception as e:
            self.logger.error(f"触发单个同步失败: {e}")
            raise
    
    def extract_folder_id_from_url(self, folder_path: str) -> str:
        """从飞书文件夹URL中提取folder_id"""
        try:
            folder_id = folder_path
            if '/folder/' in folder_path:
                try:
                    folder_id = folder_path.split('/folder/')[1].split('?')[0]
                except:
                    raise ValueError("无效的文件夹链接格式")
            
            if not folder_id:
                raise ValueError("请提供有效的文件夹链接")
            
            return folder_id
        except Exception as e:
            self.logger.error(f"提取文件夹ID失败: {e}")
            raise
    
    def scan_feishu_folder(self, folder_id: str, max_depth: int = 2, use_cache: bool = True) -> Dict[str, Any]:
        """扫描飞书文件夹获取文档列表"""
        try:
            if not folder_id:
                raise ValueError("请提供有效的文件夹ID")
            
            self.logger.info(f"开始扫描文件夹: {folder_id}, 深度: {max_depth}")
            
            try:
                # 检查飞书API配置
                import os
                if not os.getenv('FEISHU_APP_ID') or not os.getenv('FEISHU_APP_SECRET'):
                    missing_configs = []
                    if not os.getenv('FEISHU_APP_ID'):
                        missing_configs.append("FEISHU_APP_ID")
                    if not os.getenv('FEISHU_APP_SECRET'):
                        missing_configs.append("FEISHU_APP_SECRET")
                    raise ValueError(f"飞书API未配置。缺少配置: {', '.join(missing_configs)}")
                
                # 使用真实的飞书客户端获取文档
                from app.services.feishu_client import FeishuClient
                feishu_client = FeishuClient(logger=self.logger)
                all_documents = feishu_client.get_folder_documents_with_cache(
                    folder_id, use_cache=use_cache, max_depth=max_depth
                )
                
                # 统计文档类型
                type_stats = {}
                for doc in all_documents:
                    doc_type = doc.get("type", "unknown")
                    type_stats[doc_type] = type_stats.get(doc_type, 0) + 1
                
                # 计算同步状态统计（简化版本，假设所有文档都未启用同步）
                sync_enabled_count = 0
                
                return {
                    "folder_id": folder_id,
                    "total_documents": len(all_documents),
                    "type_statistics": type_stats,
                    "sync_enabled_count": sync_enabled_count,
                    "sync_disabled_count": len(all_documents) - sync_enabled_count,
                    "settings": {
                        "max_depth": max_depth,
                        "use_cache": use_cache
                    },
                    "documents": [
                        {
                            "id": doc.get("token"),  # 使用token作为id
                            "name": doc.get("name"),
                            "type": doc.get("type"),
                            "token": doc.get("token"),
                            "size": doc.get("size", 0),
                            "created_time": doc.get("created_time"),
                            "modified_time": doc.get("modified_time"),
                            "sync_enabled": False  # 简化版本，默认为false
                        }
                        for doc in all_documents
                    ]
                }
                
            except Exception as api_error:
                self.logger.error(f"从飞书获取文件夹 '{folder_id}' 内容失败: {api_error}")
                
                error_msg = str(api_error)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    raise ValueError("飞书API认证失败，请检查应用凭据配置")
                elif "403" in error_msg or "Forbidden" in error_msg:
                    raise ValueError("无权限访问该文件夹，请检查飞书应用权限或联系管理员")
                elif "404" in error_msg or "Not Found" in error_msg:
                    raise ValueError("文件夹不存在，请检查文件夹链接是否正确")
                elif "429" in error_msg or "Too Many Requests" in error_msg:
                    raise ValueError("API调用频率超限，请稍后重试")
                else:
                    raise ValueError(f"获取文件夹内容失败: {api_error}")
            
        except Exception as e:
            self.logger.error(f"扫描文件夹失败: {e}")
            raise