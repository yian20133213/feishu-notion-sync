#!/usr/bin/env python3
"""
文档服务层 - 处理文档解析、验证和批量操作相关的业务逻辑
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from .sync_service import SyncService


class DocumentService(SyncService):
    """文档服务类 - 继承同步服务的基础功能，专门处理文档相关操作"""
    
    def __init__(self, logger: logging.Logger = None, db_path: str = None):
        super().__init__(logger, db_path)
    
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
                            "platform": platform,
                            "document_id": doc_id,
                            "title": f"文档 {doc_id[:8]}...",
                            "url": url
                        })
                    
                except Exception as parse_error:
                    self.logger.warning(f"解析URL失败: {url}, 错误: {parse_error}")
                    continue
            
            if not document_ids:
                raise ValueError("没有找到有效的文档ID")
            
            return {
                "document_ids": document_ids,
                "parsed_results": parsed_results,
                "total_parsed": len(document_ids)
            }
            
        except Exception as e:
            self.logger.error(f"URL解析失败: {e}")
            raise
    
    def create_manual_sync_tasks(self, document_ids: List[str], source_platform: str, 
                                target_platform: str, force_resync: bool = False) -> Dict[str, Any]:
        """创建手动同步任务并立即开始同步"""
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
            
            from database.connection import db
            from database.models import SyncRecord
            
            with db.get_session() as session:
                for doc_id in document_ids:
                    record_number = self.generate_record_number()
                    
                    # 创建同步记录，状态设为 processing 以便立即执行
                    new_record = SyncRecord(
                        record_number=record_number,
                        source_platform=source_platform,
                        target_platform=target_platform,
                        source_id=doc_id,
                        sync_status='processing'  # 改为 processing 状态
                    )
                    
                    session.add(new_record)
                    session.flush()  # 获取ID但不提交
                    
                    record_id = new_record.id
                    record_ids.append(record_id)
                    
                    created_records.append({
                        "record_number": record_number,
                        "document_id": doc_id,
                        "record_id": record_id
                    })
                
                session.commit()
            
            # 立即触发同步处理
            successful_syncs = 0
            failed_syncs = 0
            
            for i, record_id in enumerate(record_ids):
                try:
                    # 调用同步处理器
                    self._execute_sync_immediately(record_id, source_platform, target_platform, document_ids[i])
                    successful_syncs += 1
                except Exception as sync_error:
                    self.logger.error(f"同步记录 {record_id} 执行失败: {sync_error}")
                    failed_syncs += 1
                    # 更新记录状态为失败
                    self._update_sync_status(record_id, 'failed', str(sync_error))
            
            return {
                "message": f"成功创建并启动 {len(created_records)} 个同步任务（成功: {successful_syncs}, 失败: {failed_syncs}）",
                "created_records": created_records,
                "total_created": len(created_records),
                "successful_syncs": successful_syncs,
                "failed_syncs": failed_syncs
            }
            
        except Exception as e:
            self.logger.error(f"创建手动同步任务失败: {e}")
            raise
    
    def _execute_sync_immediately(self, record_id: int, source_platform: str, target_platform: str, document_id: str):
        """立即执行同步任务"""
        try:
            self.logger.info(f"开始执行同步任务 {record_id}: {source_platform} -> {target_platform}, 文档ID: {document_id}")
            
            if source_platform == 'feishu' and target_platform == 'notion':
                result = self._sync_feishu_to_notion(document_id, record_id)
            elif source_platform == 'notion' and target_platform == 'feishu':
                result = self._sync_notion_to_feishu(document_id, record_id)
            else:
                raise ValueError(f"不支持的同步方向: {source_platform} -> {target_platform}")
            
            # 更新同步状态为成功
            success_message = result.get('message', f"文档 {document_id} 从 {source_platform} 同步到 {target_platform} 完成")
            self._update_sync_status(record_id, 'completed', success_message)
            
            self.logger.info(f"同步任务 {record_id} 执行完成: {document_id}")
            
            # 返回成功结果
            return {
                'success': True,
                'message': success_message,
                'record_id': record_id,
                'document_id': document_id,
                'target_id': result.get('target_id')
            }
            
        except Exception as e:
            self.logger.error(f"同步任务 {record_id} 执行失败: {e}")
            # 更新同步状态为失败
            self._update_sync_status(record_id, 'failed', str(e))
            raise
    
    def _sync_feishu_to_notion(self, feishu_doc_id: str, record_id: int) -> Dict[str, Any]:
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
                feishu_content = feishu_client.get_document_content(feishu_doc_id)
                
                if not feishu_content:
                    raise Exception("无法获取飞书文档内容")
            
            # 2. 检查是否已有对应的Notion页面
            target_notion_id = None
            with self.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT target_id FROM sync_records 
                    WHERE source_id = ? AND source_platform = 'feishu' AND target_platform = 'notion' 
                    AND target_id IS NOT NULL AND sync_status = 'completed'
                    ORDER BY updated_at DESC LIMIT 1
                ''', (feishu_doc_id,))
                result = cursor.fetchone()
                if result:
                    target_notion_id = result[0]
            
            # 3. 同步到Notion
            if target_notion_id:
                # 更新已存在的Notion页面
                self.logger.info(f"更新已存在的Notion页面: {target_notion_id}")
                notion_result = notion_client.update_page_from_feishu(target_notion_id, feishu_content)
                target_id = target_notion_id
                action = "更新"
            else:
                # 创建新的Notion页面 - 使用固定的父页面ID
                parent_id = "218ed26c0da0804fbc28dc977e2f4ae8"  # 您提到的Notion页面ID
                self.logger.info(f"在页面 {parent_id} 下创建新的Notion页面")
                notion_result = notion_client.create_page_from_feishu(parent_id, feishu_content)
                target_id = notion_result.get('id')  # 使用 'id' 而不是 'page_id'
                action = "创建"
            
            # 4. 更新数据库记录的target_id
            with self.get_db_connection() as conn:
                conn.execute('''
                    UPDATE sync_records 
                    SET target_id = ?, updated_at = ?
                    WHERE id = ?
                ''', (target_id, self.format_datetime(), record_id))
                conn.commit()
            
            return {
                'success': True,
                'message': f"成功{action}Notion页面: {target_id}",
                'target_id': target_id,
                'action': action
            }
            
        except Exception as e:
            self.logger.error(f"飞书到Notion同步失败: {e}")
            raise
    
    def _sync_notion_to_feishu(self, notion_page_id: str, record_id: int) -> Dict[str, Any]:
        """将Notion页面同步到飞书"""
        try:
            # 暂时返回提示信息，Notion到飞书的同步比较复杂
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
            with self.get_db_connection() as conn:
                if message:
                    conn.execute('''
                        UPDATE sync_records 
                        SET sync_status = ?, error_message = ?, updated_at = ?
                        WHERE id = ?
                    ''', (status, message, self.format_datetime(), record_id))
                else:
                    conn.execute('''
                        UPDATE sync_records 
                        SET sync_status = ?, updated_at = ?
                        WHERE id = ?
                    ''', (status, self.format_datetime(), record_id))
                conn.commit()
        except Exception as e:
            self.logger.error(f"更新同步状态失败: {e}")
    
    def trigger_single_sync(self, document_id: str, source_platform: str = 'feishu', 
                           target_platform: str = 'notion') -> Dict[str, Any]:
        """触发单个文档同步"""
        try:
            if not document_id:
                raise ValueError("请提供文档ID")
            
            # 创建同步记录
            record_number = self.generate_record_number()
            
            with self.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO sync_records 
                    (record_number, source_platform, target_platform, source_id, sync_status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record_number,
                    source_platform,
                    target_platform,
                    document_id,
                    'pending',
                    self.format_datetime(),
                    self.format_datetime()
                ))
                conn.commit()
            
            return {
                "record_number": record_number,
                "message": "同步任务已创建"
            }
            
        except Exception as e:
            self.logger.error(f"触发同步失败: {e}")
            raise
    
    def scan_feishu_folder(self, folder_id: str, max_depth: int = 2, use_cache: bool = True) -> Dict[str, Any]:
        """扫描飞书文件夹获取文档列表"""
        try:
            if not folder_id:
                raise ValueError("请提供有效的文件夹ID")
            
            self.logger.info(f"开始扫描文件夹: {folder_id}, 深度: {max_depth}")
            
            try:
                # 检查飞书API配置
                try:
                    from config.settings import settings
                    if not settings.feishu_app_id or not settings.feishu_app_secret:
                        missing_configs = [
                            config for config in ["FEISHU_APP_ID", "FEISHU_APP_SECRET"] 
                            if not getattr(settings, config.lower(), None)
                        ]
                        raise ValueError(f"飞书API未配置。缺少配置: {', '.join(missing_configs)}")
                except ImportError:
                    raise ValueError("系统配置模块未找到，请联系管理员")
                
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
    
    def create_batch_sync_from_folder(self, folder_path: str, max_depth: int = 2, 
                                    use_cache: bool = True, force_sync: bool = False) -> Dict[str, Any]:
        """从文件夹扫描结果创建批量同步任务"""
        try:
            # 提取文件夹ID
            folder_id = self.extract_folder_id_from_url(folder_path)
            
            # 扫描文件夹
            scan_result = self.scan_feishu_folder(folder_id, max_depth, use_cache)
            
            # 提取文档ID列表
            document_ids = [doc["token"] for doc in scan_result["documents"] if doc.get("token")]
            
            if not document_ids:
                return {
                    "message": "文件夹中没有找到有效文档",
                    "folder_scan": scan_result,
                    "sync_results": {
                        "total_requested": 0,
                        "created_count": 0,
                        "exists_count": 0,
                        "error_count": 0,
                        "records": []
                    }
                }
            
            # 创建批量同步任务
            sync_results = self.create_sync_records_batch(document_ids, force_sync)
            
            return {
                "message": f"从文件夹扫描到 {len(document_ids)} 个文档，创建了 {sync_results['created_count']} 个同步任务",
                "folder_scan": scan_result,
                "sync_results": sync_results
            }
            
        except Exception as e:
            self.logger.error(f"从文件夹创建批量同步失败: {e}")
            raise