"""
Notion API client for page and database operations
"""
import requests
import json
from typing import Dict, List, Optional, Any
import logging

from config import settings

logger = logging.getLogger(__name__)


class NotionClient:
    """Notion API客户端"""
    
    def __init__(self):
        self.token = settings.notion_token
        self.base_url = "https://api.notion.com/v1"
        self.version = "2022-06-28"
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """通用API请求方法"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": self.version
        }
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Successfully made {method} request to {endpoint}")
            return result
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                error_detail = e.response.json()
                logger.error(f"Bad request to {endpoint}: {error_detail}")
            elif e.response.status_code == 401:
                logger.error(f"Unauthorized request to {endpoint}: Check token")
            elif e.response.status_code == 404:
                logger.error(f"Resource not found: {endpoint}")
            else:
                logger.error(f"HTTP error {e.response.status_code} for {endpoint}: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            raise
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """获取页面信息"""
        endpoint = f"pages/{page_id}"
        
        try:
            result = self._make_request("GET", endpoint)
            logger.info(f"Successfully retrieved page {page_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error getting page {page_id}: {e}")
            raise
    
    def get_page_content(self, page_id: str) -> List[Dict[str, Any]]:
        """获取页面内容块"""
        endpoint = f"blocks/{page_id}/children"
        
        try:
            result = self._make_request("GET", endpoint)
            blocks = result.get("results", [])
            logger.info(f"Successfully retrieved {len(blocks)} blocks from page {page_id}")
            return blocks
        
        except Exception as e:
            logger.error(f"Error getting page content for {page_id}: {e}")
            raise
    
    def create_page(self, parent_id: str, title: str, content_blocks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建新页面"""
        endpoint = "pages"
        
        data = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        }
        
        if content_blocks:
            data["children"] = content_blocks
        
        try:
            result = self._make_request("POST", endpoint, json=data)
            logger.info(f"Successfully created page '{title}' under {parent_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error creating page '{title}': {e}")
            raise
    
    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """更新页面属性"""
        endpoint = f"pages/{page_id}"
        
        data = {"properties": properties}
        
        try:
            result = self._make_request("PATCH", endpoint, json=data)
            logger.info(f"Successfully updated page {page_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error updating page {page_id}: {e}")
            raise
    
    def append_blocks(self, page_id: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """向页面添加内容块"""
        endpoint = f"blocks/{page_id}/children"
        
        data = {"children": blocks}
        
        try:
            result = self._make_request("PATCH", endpoint, json=data)
            logger.info(f"Successfully appended {len(blocks)} blocks to page {page_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error appending blocks to page {page_id}: {e}")
            raise
    
    def update_block(self, block_id: str, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新内容块"""
        endpoint = f"blocks/{block_id}"
        
        try:
            result = self._make_request("PATCH", endpoint, json=block_data)
            logger.info(f"Successfully updated block {block_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error updating block {block_id}: {e}")
            raise
    
    def delete_block(self, block_id: str) -> Dict[str, Any]:
        """删除内容块"""
        endpoint = f"blocks/{block_id}"
        
        try:
            result = self._make_request("DELETE", endpoint)
            logger.info(f"Successfully deleted block {block_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error deleting block {block_id}: {e}")
            raise
    
    def get_database(self, database_id: str) -> Dict[str, Any]:
        """获取数据库信息"""
        endpoint = f"databases/{database_id}"
        
        try:
            result = self._make_request("GET", endpoint)
            logger.info(f"Successfully retrieved database {database_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error getting database {database_id}: {e}")
            raise
    
    def query_database(self, database_id: str, filter_data: Dict[str, Any] = None, sorts: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """查询数据库"""
        endpoint = f"databases/{database_id}/query"
        
        data = {}
        if filter_data:
            data["filter"] = filter_data
        if sorts:
            data["sorts"] = sorts
        
        try:
            result = self._make_request("POST", endpoint, json=data)
            pages = result.get("results", [])
            logger.info(f"Successfully queried database {database_id}, got {len(pages)} results")
            return pages
        
        except Exception as e:
            logger.error(f"Error querying database {database_id}: {e}")
            raise
    
    def create_database_page(self, database_id: str, properties: Dict[str, Any], content_blocks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """在数据库中创建页面"""
        endpoint = "pages"
        
        data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        if content_blocks:
            data["children"] = content_blocks
        
        try:
            result = self._make_request("POST", endpoint, json=data)
            logger.info(f"Successfully created database page in {database_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error creating database page in {database_id}: {e}")
            raise
    
    def search(self, query: str = "", filter_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """搜索页面和数据库"""
        endpoint = "search"
        
        data = {}
        if query:
            data["query"] = query
        if filter_data:
            data["filter"] = filter_data
        
        try:
            result = self._make_request("POST", endpoint, json=data)
            results = result.get("results", [])
            logger.info(f"Successfully searched Notion, got {len(results)} results")
            return results
        
        except Exception as e:
            logger.error(f"Error searching Notion: {e}")
            raise
    
    def convert_feishu_to_notion_blocks(self, feishu_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将飞书文档内容转换为Notion块"""
        notion_blocks = []
        
        try:
            blocks = feishu_content.get("blocks", [])
            
            for block in blocks:
                notion_block = self._convert_block(block)
                if notion_block:
                    notion_blocks.append(notion_block)
            
            logger.info(f"Successfully converted {len(blocks)} Feishu blocks to {len(notion_blocks)} Notion blocks")
            return notion_blocks
            
        except Exception as e:
            logger.error(f"Error converting Feishu content to Notion blocks: {e}")
            raise
    
    def _convert_block(self, feishu_block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """转换单个飞书块为Notion块"""
        try:
            block_type = feishu_block.get("type")
            content = feishu_block.get("content", "")
            
            if block_type == "text":
                # 普通文本
                return {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._create_rich_text(content)
                    }
                }
            
            elif block_type in ["heading1", "heading2", "heading3"]:
                # 标题
                level = feishu_block.get("level", 1)
                heading_type = f"heading_{level}"
                
                return {
                    "object": "block",
                    "type": heading_type,
                    heading_type: {
                        "rich_text": self._create_rich_text(content)
                    }
                }
            
            elif block_type == "bullet":
                # 无序列表
                return {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": self._create_rich_text(content)
                    }
                }
            
            elif block_type == "ordered":
                # 有序列表
                return {
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": self._create_rich_text(content)
                    }
                }
            
            elif block_type == "code":
                # 代码块
                code_content = content
                language = "plain text"
                
                if isinstance(content, dict):
                    code_content = content.get("code", "")
                    language = content.get("language", "plain text")
                
                return {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": self._create_rich_text(code_content),
                        "language": self._map_language(language)
                    }
                }
            
            elif block_type == "quote":
                # 引用块
                return {
                    "object": "block",
                    "type": "quote",
                    "quote": {
                        "rich_text": self._create_rich_text(content)
                    }
                }
            
            elif block_type == "equation":
                # 公式块
                return {
                    "object": "block",
                    "type": "equation",
                    "equation": {
                        "expression": content
                    }
                }
            
            elif block_type == "image":
                # 图片块 - 需要先处理图片上传
                file_token = feishu_block.get("file_token", "")
                alt_text = feishu_block.get("alt_text", "")
                
                # 这里会返回一个占位符，实际图片处理在后续步骤
                return {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._create_rich_text(f"[图片: {alt_text}] (飞书文件Token: {file_token})")
                    }
                }
            
            elif block_type == "table":
                # 表格块 - Notion表格结构较复杂，先转为简单文本
                return {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._create_rich_text("[表格内容] - 需手动转换")
                    }
                }
            
            else:
                # 未知类型，转为普通文本
                logger.warning(f"Unknown block type: {block_type}")
                return {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._create_rich_text(f"[{block_type}] {content}")
                    }
                }
        
        except Exception as e:
            logger.error(f"Error converting block: {e}")
            return None
    
    def _create_rich_text(self, content: str) -> List[Dict[str, Any]]:
        """创建Notion富文本对象"""
        if not content:
            return []
        
        # 简单处理，可以扩展支持更多格式
        return [
            {
                "type": "text",
                "text": {
                    "content": content
                }
            }
        ]
    
    def _map_language(self, feishu_language: str) -> str:
        """映射飞书语言代码到Notion支持的语言"""
        language_map = {
            "javascript": "javascript",
            "python": "python",
            "java": "java",
            "html": "html",
            "css": "css",
            "sql": "sql",
            "json": "json",
            "xml": "xml",
            "yaml": "yaml",
            "markdown": "markdown",
            "shell": "shell",
            "bash": "shell",
            "typescript": "typescript",
            "go": "go",
            "rust": "rust",
            "c": "c",
            "cpp": "c++",
            "php": "php",
            "ruby": "ruby"
        }
        
        return language_map.get(feishu_language.lower(), "plain text")
    
    def create_page_from_feishu(self, parent_id: str, feishu_content: Dict[str, Any]) -> Dict[str, Any]:
        """从飞书内容创建Notion页面"""
        try:
            title = feishu_content.get("title", "未命名文档")
            blocks = self.convert_feishu_to_notion_blocks(feishu_content)
            
            # 创建页面
            page_data = self.create_page(parent_id, title, blocks)
            
            logger.info(f"Successfully created Notion page '{title}' from Feishu content")
            return page_data
            
        except Exception as e:
            logger.error(f"Error creating Notion page from Feishu content: {e}")
            raise
    
    def update_page_from_feishu(self, page_id: str, feishu_content: Dict[str, Any]) -> Dict[str, Any]:
        """用飞书内容更新Notion页面"""
        try:
            title = feishu_content.get("title", "未命名文档")
            
            # 更新页面标题
            properties = {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
            
            self.update_page(page_id, properties)
            
            # 获取现有内容块并删除
            existing_blocks = self.get_page_content(page_id)
            for block in existing_blocks:
                if block.get("type") != "child_page":  # 保留子页面
                    self.delete_block(block["id"])
            
            # 添加新内容
            new_blocks = self.convert_feishu_to_notion_blocks(feishu_content)
            if new_blocks:
                self.append_blocks(page_id, new_blocks)
            
            logger.info(f"Successfully updated Notion page {page_id} from Feishu content")
            return {"success": True, "page_id": page_id}
            
        except Exception as e:
            logger.error(f"Error updating Notion page from Feishu content: {e}")
            raise