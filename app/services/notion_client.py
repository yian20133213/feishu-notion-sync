"""
Notion API client for page and database operations
"""
import httpx
import json
from typing import Dict, List, Optional, Any
import logging

from config import settings

logger = logging.getLogger(__name__)


class NotionClient:
    """Notion API客户端"""
    
    def __init__(self, token=None, logger=None):
        self.token = token or settings.notion_token
        self.base_url = "https://api.notion.com/v1"
        self.version = "2022-06-28"
        self.logger = logger or logging.getLogger(__name__)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """通用API请求方法"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": self.version
        }
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            with httpx.Client() as client:
                response = client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
            
            result = response.json()
            logger.info(f"Successfully made {method} request to {endpoint}")
            return result
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Bad request to {endpoint}: {error_detail}")
                except:
                    logger.error(f"Bad request to {endpoint}: {e.response.text}")
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
    
    def test_connection(self, database_id=None) -> Dict[str, Any]:
        """测试Notion API连接"""
        try:
            # 测试用户信息接口
            endpoint = "users/me"
            result = self._make_request("GET", endpoint)
            
            if result.get("object") == "user":
                user_info = {
                    "success": True,
                    "message": "Notion API连接正常",
                    "user_name": result.get("name", ""),
                    "user_id": result.get("id", ""),
                    "user_type": result.get("type", "")
                }
                
                # 如果提供了数据库ID，测试数据库访问
                if database_id:
                    try:
                        db_result = self._make_request("GET", f"databases/{database_id}")
                        user_info["database_access"] = True
                        user_info["database_title"] = db_result.get("title", [{}])[0].get("plain_text", "")
                    except Exception as e:
                        user_info["database_access"] = False
                        user_info["database_error"] = str(e)
                
                return user_info
            else:
                return {
                    "success": False,
                    "message": "API响应格式异常"
                }
                
        except Exception as e:
            self.logger.error(f"测试Notion API连接失败: {e}")
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}"
            }
    
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
    
    def create_page(self, parent_id: str, title: str, content_blocks: List[Dict[str, Any]] = None, category: str = None, page_type: str = None) -> Dict[str, Any]:
        """创建新页面"""
        endpoint = "pages"
        
        # 判断父级是页面还是数据库
        # 检查是否为数据库ID（可能是32位无连字符，或36位有连字符格式）
        is_database_id = (len(parent_id) == 32 and "-" not in parent_id) or \
                        (len(parent_id) == 36 and parent_id.count("-") == 4)
        
        if is_database_id:
            # 看起来像数据库ID，使用数据库作为父级
            data = {
                "parent": {"database_id": parent_id},
                "properties": {
                    "title": {  # 使用实际的title属性
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    },
                    "status": {  # 设置状态为已发布
                        "select": {
                            "name": "Published"
                        }
                    },
                    "type": {  # 设置类型
                        "select": {
                            "name": page_type or "Post"
                        }
                    }
                }
            }
            
            # 如果指定了分类，则设置分类属性
            if category:
                data["properties"]["category"] = {
                    "select": {
                        "name": category
                    }
                }
            else:
                # 默认分类
                data["properties"]["category"] = {
                    "select": {
                        "name": "技术分享"
                    }
                }
        else:
            # 使用页面作为父级
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
    
    def create_page_in_database(self, database_id: str, title: str, content_blocks: List[Dict[str, Any]] = None, category: str = None, page_type: str = None) -> Dict[str, Any]:
        """在指定数据库中创建新页面"""
        endpoint = "pages"
        
        data = {
            "parent": {"database_id": database_id},
            "properties": {
                "title": {  # 使用实际的title属性
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "status": {  # 设置状态为已发布
                    "select": {
                        "name": "Published"
                    }
                },
                "type": {  # 设置类型
                    "select": {
                        "name": page_type or "Post"
                    }
                }
            }
        }
        
        # 如果指定了分类，则设置分类属性
        if category:
            data["properties"]["category"] = {
                "select": {
                    "name": category
                }
            }
        else:
            # 默认分类
            data["properties"]["category"] = {
                "select": {
                    "name": "技术分享"
                }
            }
        
        if content_blocks:
            data["children"] = content_blocks
        
        try:
            result = self._make_request("POST", endpoint, json=data)
            logger.info(f"Successfully created page '{title}' in database {database_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error creating page '{title}' in database {database_id}: {e}")
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
    
    def update_page_content(self, page_id: str, title: str, content_blocks: List[Dict[str, Any]] = None, category: str = None, page_type: str = None) -> Dict[str, Any]:
        """更新页面内容和属性"""
        try:
            # 1. 更新页面属性（标题、分类、类型等）
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
            
            # 如果指定了分类，则设置分类属性
            if category:
                properties["category"] = {
                    "select": {
                        "name": category
                    }
                }
            
            # 如果指定了页面类型，则设置类型属性
            if page_type:
                properties["type"] = {
                    "select": {
                        "name": page_type
                    }
                }
            
            # 更新页面属性
            update_result = self.update_page(page_id, properties)
            
            # 2. 如果有内容块，则更新页面内容
            if content_blocks:
                # 首先获取现有的子块
                children_response = self._make_request("GET", f"blocks/{page_id}/children")
                existing_blocks = children_response.get('results', [])
                
                # 删除现有的内容块（保留页面结构）
                for block in existing_blocks:
                    if block.get('type') in ['paragraph', 'heading_1', 'heading_2', 'heading_3', 'bulleted_list_item', 'numbered_list_item']:
                        try:
                            self._make_request("DELETE", f"blocks/{block['id']}")
                        except Exception as e:
                            logger.warning(f"Failed to delete block {block['id']}: {e}")
                
                # 添加新的内容块
                if content_blocks:
                    self.append_blocks(page_id, content_blocks)
            
            logger.info(f"Successfully updated page content for {page_id}")
            return {"success": True, "id": page_id}
            
        except Exception as e:
            logger.error(f"Error updating page content {page_id}: {e}")
            return {"success": False, "error": str(e)}
    
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
    
    def find_page_in_database_by_title(self, database_id: str, title: str) -> Optional[Dict[str, Any]]:
        """在数据库中根据标题查找页面"""
        try:
            # 构建查询过滤器
            filter_data = {
                "property": "title",
                "title": {
                    "equals": title
                }
            }
            
            result = self.query_database(database_id, filter_data)
            
            if result:
                logger.info(f"Found existing page with title '{title}' in database {database_id}")
                return result[0]  # 返回第一个匹配的页面
            else:
                logger.info(f"No page found with title '{title}' in database {database_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching for page in database {database_id}: {e}")
            return None
    
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
                # 图片块 - 检查是否已经处理了图片上传
                file_token = feishu_block.get("file_token", "")
                alt_text = feishu_block.get("alt_text", "")
                cdn_url = feishu_block.get("cdn_url", "")
                
                # 如果图片已经上传到CDN，创建真正的图片块
                if cdn_url:
                    return {
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
                    }
                else:
                    # 图片尚未处理，返回占位符（这种情况应该很少出现）
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
    
    def get_database_properties(self, database_id: str) -> Dict[str, Any]:
        """获取数据库的属性配置，包括分类选项"""
        try:
            database = self.get_database(database_id)
            properties = database.get("properties", {})
            
            # 提取分类字段的选项
            category_options = []
            type_options = []
            
            for prop_name, prop_config in properties.items():
                prop_type = prop_config.get("type", "")
                
                if prop_type == "select":
                    # 处理单选类型的属性
                    options = prop_config.get("select", {}).get("options", [])
                    
                    # 根据属性名判断是类型还是分类
                    if prop_name.lower() in ["category", "分类", "类别"]:
                        category_options = [opt.get("name", "") for opt in options]
                    elif prop_name.lower() in ["type", "类型"]:
                        type_options = [opt.get("name", "") for opt in options]
            
            result = {
                "database_id": database_id,
                "title": database.get("title", [{}])[0].get("plain_text", ""),
                "categories": category_options,
                "types": type_options,
                "properties": properties
            }
            
            logger.info(f"Successfully retrieved database properties for {database_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting database properties for {database_id}: {e}")
            raise
    
    def create_page_from_feishu(self, parent_id: str, feishu_content: Dict[str, Any], category: str = None) -> Dict[str, Any]:
        """从飞书内容创建Notion页面"""
        try:
            title = feishu_content.get("title", "未命名文档")
            blocks = self.convert_feishu_to_notion_blocks(feishu_content)
            
            # 创建页面，传入分类参数
            page_data = self.create_page(parent_id, title, blocks, category)
            
            logger.info(f"Successfully created Notion page '{title}' from Feishu content with category '{category}'")
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