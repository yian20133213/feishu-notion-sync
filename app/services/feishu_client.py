"""
Feishu API client for document and event handling
"""
import requests
import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional, Any
import logging

from config import settings

logger = logging.getLogger(__name__)


class FeishuClient:
    """飞书API客户端"""
    
    def __init__(self):
        self.app_id = settings.feishu_app_id
        self.app_secret = settings.feishu_app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        self._access_token = None
        self._token_expires_at = 0
    
    def _get_access_token(self) -> str:
        """获取访问令牌"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        url = f"{self.base_url}/auth/v3/app_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                self._access_token = result["app_access_token"]
                # Token expires in 2 hours, refresh 10 minutes early
                self._token_expires_at = time.time() + result["expire"] - 600
                logger.info("Successfully obtained Feishu access token")
                return self._access_token
            else:
                logger.error(f"Failed to get access token: {result}")
                raise Exception(f"Failed to get access token: {result}")
        
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            raise
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """通用API请求方法"""
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                return result
            else:
                logger.error(f"API request failed: {result}")
                raise Exception(f"API request failed: {result}")
        
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            raise
    
    def verify_webhook_signature(self, timestamp: str, nonce: str, body: str, signature: str) -> bool:
        """验证Webhook签名"""
        try:
            # 按照飞书文档要求构建待签名字符串
            sign_str = f"{timestamp}{nonce}{self.app_secret}{body}"
            
            # 计算签名
            calculated_signature = hmac.new(
                self.app_secret.encode('utf-8'),
                sign_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return calculated_signature == signature
        
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def get_document_content(self, document_id: str) -> Dict[str, Any]:
        """获取文档内容"""
        endpoint = f"docx/v1/documents/{document_id}/content"
        
        try:
            result = self._make_request("GET", endpoint)
            logger.info(f"Successfully retrieved document content for {document_id}")
            return result.get("data", {})
        
        except Exception as e:
            logger.error(f"Error getting document content for {document_id}: {e}")
            raise
    
    def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """获取文档基本信息"""
        endpoint = f"drive/v1/files/{document_id}"
        
        try:
            result = self._make_request("GET", endpoint)
            logger.info(f"Successfully retrieved document info for {document_id}")
            return result.get("data", {})
        
        except Exception as e:
            logger.error(f"Error getting document info for {document_id}: {e}")
            raise
    
    def list_files_in_folder(self, folder_id: str, page_size: int = 50) -> List[Dict[str, Any]]:
        """列出文件夹中的文件"""
        endpoint = "drive/v1/files"
        params = {
            "parent_token": folder_id,
            "page_size": page_size
        }
        
        try:
            result = self._make_request("GET", endpoint, params=params)
            files = result.get("data", {}).get("files", [])
            logger.info(f"Successfully retrieved {len(files)} files from folder {folder_id}")
            return files
        
        except Exception as e:
            logger.error(f"Error listing files in folder {folder_id}: {e}")
            raise
    
    def download_file(self, file_token: str) -> bytes:
        """下载文件内容"""
        endpoint = f"drive/v1/files/{file_token}/download"
        
        try:
            token = self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Successfully downloaded file {file_token}")
            return response.content
        
        except Exception as e:
            logger.error(f"Error downloading file {file_token}: {e}")
            raise
    
    def get_bitable_tables(self, app_token: str) -> List[Dict[str, Any]]:
        """获取多维表格的表格列表"""
        endpoint = f"bitable/v1/apps/{app_token}/tables"
        
        try:
            result = self._make_request("GET", endpoint)
            tables = result.get("data", {}).get("items", [])
            logger.info(f"Successfully retrieved {len(tables)} tables from bitable {app_token}")
            return tables
        
        except Exception as e:
            logger.error(f"Error getting bitable tables for {app_token}: {e}")
            raise
    
    def get_bitable_records(self, app_token: str, table_id: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """获取多维表格记录"""
        endpoint = f"bitable/v1/apps/{app_token}/tables/{table_id}/records"
        params = {"page_size": page_size}
        
        try:
            result = self._make_request("GET", endpoint, params=params)
            records = result.get("data", {}).get("items", [])
            logger.info(f"Successfully retrieved {len(records)} records from table {table_id}")
            return records
        
        except Exception as e:
            logger.error(f"Error getting bitable records for {app_token}/{table_id}: {e}")
            raise
    
    def parse_document_content(self, document_id: str) -> Dict[str, Any]:
        """解析文档内容为结构化数据"""
        try:
            # 获取文档基本信息
            doc_info = self.get_document_info(document_id)
            
            # 获取文档内容
            content_data = self.get_document_content(document_id)
            
            # 解析文档结构
            parsed_content = {
                "title": doc_info.get("name", "未命名文档"),
                "document_id": document_id,
                "type": "document",
                "blocks": [],
                "images": [],
                "metadata": {
                    "created_time": doc_info.get("created_time"),
                    "modified_time": doc_info.get("modified_time"),
                    "owner_id": doc_info.get("owner_id"),
                    "size": doc_info.get("size", 0)
                }
            }
            
            # 解析文档块内容
            document = content_data.get("document", {})
            blocks = document.get("blocks", {})
            
            for block_id, block_data in blocks.items():
                parsed_block = self._parse_block(block_id, block_data)
                if parsed_block:
                    parsed_content["blocks"].append(parsed_block)
                    
                    # 提取图片信息
                    if parsed_block.get("type") == "image":
                        parsed_content["images"].append({
                            "block_id": block_id,
                            "file_token": parsed_block.get("file_token"),
                            "alt_text": parsed_block.get("alt_text", "")
                        })
            
            logger.info(f"Successfully parsed document {document_id} with {len(parsed_content['blocks'])} blocks")
            return parsed_content
            
        except Exception as e:
            logger.error(f"Error parsing document content for {document_id}: {e}")
            raise
    
    def _parse_block(self, block_id: str, block_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析单个文档块"""
        try:
            block_type = block_data.get("block_type")
            
            if not block_type:
                return None
            
            parsed_block = {
                "id": block_id,
                "type": block_type,
                "parent_id": block_data.get("parent_id"),
                "children": block_data.get("children", [])
            }
            
            # 根据块类型解析内容
            if block_type == "page":
                # 页面块
                elements = block_data.get("page", {}).get("elements", [])
                parsed_block["content"] = self._parse_page_elements(elements)
                
            elif block_type == "text":
                # 文本块
                text_run = block_data.get("text", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(text_run)
                
            elif block_type == "heading1":
                # 一级标题
                elements = block_data.get("heading1", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                parsed_block["level"] = 1
                
            elif block_type == "heading2":
                # 二级标题
                elements = block_data.get("heading2", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                parsed_block["level"] = 2
                
            elif block_type == "heading3":
                # 三级标题
                elements = block_data.get("heading3", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                parsed_block["level"] = 3
                
            elif block_type == "bullet":
                # 无序列表
                elements = block_data.get("bullet", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                
            elif block_type == "ordered":
                # 有序列表
                elements = block_data.get("ordered", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                
            elif block_type == "code":
                # 代码块
                code_data = block_data.get("code", {})
                parsed_block["content"] = {
                    "language": code_data.get("language", ""),
                    "code": self._parse_text_elements(code_data.get("elements", []))
                }
                
            elif block_type == "quote":
                # 引用块
                elements = block_data.get("quote", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                
            elif block_type == "equation":
                # 公式块
                equation_data = block_data.get("equation", {})
                parsed_block["content"] = equation_data.get("content", "")
                
            elif block_type == "image":
                # 图片块
                image_data = block_data.get("image", {})
                parsed_block["file_token"] = image_data.get("file_token", "")
                parsed_block["alt_text"] = image_data.get("alt", {}).get("content", "")
                parsed_block["width"] = image_data.get("width", 0)
                parsed_block["height"] = image_data.get("height", 0)
                
            elif block_type == "table":
                # 表格块
                table_data = block_data.get("table", {})
                parsed_block["content"] = {
                    "rows": table_data.get("table_rows", []),
                    "columns": table_data.get("table_columns", [])
                }
                
            return parsed_block
            
        except Exception as e:
            logger.error(f"Error parsing block {block_id}: {e}")
            return None
    
    def _parse_page_elements(self, elements: List[Dict[str, Any]]) -> str:
        """解析页面元素"""
        content_parts = []
        
        for element in elements:
            if element.get("type") == "text_run":
                text_run = element.get("text_run", {})
                content = text_run.get("content", "")
                content_parts.append(content)
        
        return "".join(content_parts)
    
    def _parse_text_elements(self, elements: List[Dict[str, Any]]) -> str:
        """解析文本元素"""
        content_parts = []
        
        for element in elements:
            if element.get("type") == "text_run":
                text_run = element.get("text_run", {})
                content = text_run.get("content", "")
                
                # 处理文本样式（可选，用于保留格式）
                text_style = text_run.get("text_element_style", {})
                if text_style.get("bold"):
                    content = f"**{content}**"
                if text_style.get("italic"):
                    content = f"*{content}*"
                if text_style.get("strikethrough"):
                    content = f"~~{content}~~"
                if text_style.get("underline"):
                    content = f"__{content}__"
                
                content_parts.append(content)
        
        return "".join(content_parts)
    
    def get_image_download_url(self, file_token: str) -> str:
        """获取图片下载链接"""
        try:
            token = self._get_access_token()
            download_url = f"{self.base_url}/drive/v1/files/{file_token}/download"
            
            logger.info(f"Generated download URL for image {file_token}")
            return download_url
            
        except Exception as e:
            logger.error(f"Error generating download URL for image {file_token}: {e}")
            raise