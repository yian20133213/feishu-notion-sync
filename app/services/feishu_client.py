"""
Feishu API client for document and event handling
"""
import httpx
import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional, Any
import logging

from config import settings

class FeishuClient:
    """飞书API客户端"""
    
    def __init__(self, logger=None):
        self.app_id = settings.feishu_app_id
        self.app_secret = settings.feishu_app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        self._access_token = None
        self._token_expires_at = 0
        self.logger = logger or logging.getLogger(__name__)
    
    def _get_access_token(self) -> str:
        """获取访问令牌"""
        if not self.app_id or not self.app_secret:
            raise Exception("飞书应用配置未设置，请检查 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量")
        
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        url = f"{self.base_url}/auth/v3/app_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=data)
                response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                self._access_token = result["app_access_token"]
                # Token expires in 2 hours, refresh 10 minutes early
                self._token_expires_at = time.time() + result["expire"] - 600
                self.logger.info("Successfully obtained Feishu access token")
                return self._access_token
            else:
                self.logger.error(f"Failed to get access token: {result}")
                raise Exception(f"Failed to get access token: {result}")
        
        except Exception as e:
            self.logger.error(f"Error getting access token: {e}")
            raise
    
    def get_access_token(self) -> str:
        """公开方法获取访问令牌"""
        return self._get_access_token()
    
    def test_connection(self) -> Dict[str, Any]:
        """测试飞书API连接"""
        try:
            # 首先测试获取访问令牌
            token = self._get_access_token()
            if not token:
                return {"success": False, "message": "无法获取访问令牌"}
            
            # 简单测试 - 只测试token获取
            return {
                "success": True,
                "message": "飞书API连接正常",
                "token_status": "成功获取访问令牌",
                "app_id": self.app_id[:20] + "***" if len(self.app_id) > 20 else self.app_id
            }
                
        except Exception as e:
            self.logger.error(f"测试飞书API连接失败: {e}")
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}"
            }
    
    def _make_request(self, method: str, endpoint: str, retry_count: int = 0, **kwargs) -> Dict[str, Any]:
        """通用API请求方法，带有重试机制"""
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            with httpx.Client() as client:
                response = client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                return result
            else:
                self.logger.error(f"API request failed: {result}")
                raise Exception(f"API request failed: {result}")
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and retry_count < 3:  # 最多重试3次
                wait_time = (retry_count + 1) * 2  # 递增等待时间: 2s, 4s, 6s
                self.logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {retry_count + 1}/3")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, retry_count + 1, **kwargs)
            else:
                self.logger.error(f"Error making request to {endpoint}: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Error making request to {endpoint}: {e}")
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
            self.logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def get_document_content(self, document_id: str) -> Dict[str, Any]:
        """获取文档内容"""
        # 首先尝试新的blocks API端点
        endpoint = f"docx/v1/documents/{document_id}/blocks"
        
        try:
            result = self._make_request("GET", endpoint)
            if result.get("code") == 0 and result.get("data", {}).get("items"):
                self.logger.info(f"Successfully retrieved document blocks for {document_id}")
                return {
                    "document": {
                        "blocks": {item["block_id"]: item for item in result.get("data", {}).get("items", [])},
                        "title": self._extract_title_from_blocks(result.get("data", {}).get("items", [])),
                        "document_id": document_id
                    },
                    "api_source": "blocks"
                }
        except Exception as blocks_error:
            self.logger.warning(f"Blocks API failed for {document_id}: {blocks_error}")
            
            # 尝试旧的content API端点
            endpoint = f"docx/v1/documents/{document_id}/content"
            
            try:
                result = self._make_request("GET", endpoint)
                self.logger.info(f"Successfully retrieved document content for {document_id}")
                return result.get("data", {})
            
            except Exception as e:
                error_msg = f"获取飞书文档内容失败 (文档ID: {document_id}): {str(e)}"
                self.logger.error(error_msg)
                
                # 检查错误类型并提供具体建议
                if "401" in str(e) or "Unauthorized" in str(e):
                    raise Exception(f"{error_msg}\n建议：检查飞书应用凭据配置和权限设置")
                elif "403" in str(e) or "Forbidden" in str(e):
                    raise Exception(f"{error_msg}\n建议：确认应用对此文档有访问权限")
                elif "404" in str(e) or "Not Found" in str(e):
                    # 尝试获取基本文档信息作为备选方案
                    try:
                        self.logger.info(f"Content API failed, trying to get basic document info for {document_id}")
                        doc_info = self.get_document_basic_info(document_id)
                        if doc_info:
                            self.logger.info(f"Successfully retrieved basic document info as fallback for {document_id}")
                            return {
                                "document": {
                                    "title": doc_info.get("title", "未知标题"),
                                    "document_id": document_id
                                },
                                "fallback_mode": True,
                                "message": "由于权限限制，仅获取了基本信息"
                            }
                    except Exception as fallback_e:
                        self.logger.error(f"Fallback to basic info also failed: {fallback_e}")
                    
                    raise Exception(f"{error_msg}\n建议：\n1. 检查文档ID是否正确\n2. 确认文档是否存在且未被删除\n3. 确认当前飞书应用有访问该文档的权限\n4. 如果是企业文档，确认应用已被授权访问")
                elif "429" in str(e) or "Too Many Requests" in str(e):
                    raise Exception(f"{error_msg}\n建议：API调用频率过高，请稍后重试")
                else:
                    raise Exception(error_msg)
    
    def _extract_title_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """从blocks中提取文档标题"""
        for block in blocks:
            if block.get("block_type") == 1 and block.get("page"):  # 页面块，通常包含标题
                elements = block.get("page", {}).get("elements", [])
                if elements and elements[0].get("text_run"):
                    return elements[0]["text_run"]["content"]
        return "未知标题"
    
    def get_document_basic_info(self, document_id: str) -> Dict[str, Any]:
        """获取文档基本信息（仅标题等基础信息）"""
        endpoint = f"docx/v1/documents/{document_id}"
        
        try:
            result = self._make_request("GET", endpoint)
            self.logger.info(f"Successfully retrieved basic document info for {document_id}")
            document_data = result.get("data", {}).get("document", {})
            return {
                "title": document_data.get("title", ""),
                "document_id": document_data.get("document_id", document_id),
                "revision_id": document_data.get("revision_id", 0)
            }
        except Exception as e:
            self.logger.error(f"Error getting basic document info for {document_id}: {e}")
            raise

    def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """获取文档基本信息"""
        endpoint = f"drive/v1/files/{document_id}"
        
        try:
            result = self._make_request("GET", endpoint)
            self.logger.info(f"Successfully retrieved document info for {document_id}")
            return result.get("data", {})
        
        except Exception as e:
            error_msg = f"获取飞书文档信息失败 (文档ID: {document_id}): {str(e)}"
            self.logger.error(error_msg)
            
            # 检查错误类型并提供具体建议
            if "401" in str(e) or "Unauthorized" in str(e):
                raise Exception(f"{error_msg}\n建议：检查飞书应用凭据配置和权限设置")
            elif "403" in str(e) or "Forbidden" in str(e):
                raise Exception(f"{error_msg}\n建议：确认应用对此文档有访问权限")
            elif "404" in str(e) or "Not Found" in str(e):
                # 尝试使用document API作为备选方案
                try:
                    self.logger.info(f"Drive API failed, trying document API for {document_id}")
                    doc_info = self.get_document_basic_info(document_id)
                    if doc_info:
                        self.logger.info(f"Successfully retrieved document info via fallback API for {document_id}")
                        return {
                            "file": {
                                "name": doc_info.get("title", "未知标题"),
                                "token": document_id,
                                "type": "docx"
                            },
                            "fallback_mode": True
                        }
                except Exception as fallback_e:
                    self.logger.error(f"Fallback to document API also failed: {fallback_e}")
                
                raise Exception(f"{error_msg}\n建议：\n1. 检查文档ID是否正确\n2. 确认文档是否存在且未被删除\n3. 确认当前飞书应用有访问该文档的权限\n4. 如果是企业文档，确认应用已被授权访问")
            elif "429" in str(e) or "Too Many Requests" in str(e):
                raise Exception(f"{error_msg}\n建议：API调用频率过高，请稍后重试")
            else:
                raise Exception(error_msg)
    
    def list_files_in_folder(self, folder_id: str, page_size: int = 100, page_token: Optional[str] = None) -> Dict[str, Any]:
        """列出文件夹中的文件，支持分页"""
        endpoint = "drive/v1/files"
        params = {
            "folder_token": folder_id,
            "page_size": page_size,
        }
        if page_token:
            params["page_token"] = page_token
        
        try:
            result = self._make_request("GET", endpoint, params=params)
            data = result.get("data", {})
            files = data.get("files", [])
            self.logger.info(f"Successfully retrieved {len(files)} items from folder {folder_id}")
            return data
        
        except Exception as e:
            # 尝试解析更详细的错误信息
            error_details = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    error_details = f"API Error: {error_json.get('msg', str(error_json))}"
                except:
                    pass # Keep original error if response is not json
            self.logger.error(f"Error listing files in folder {folder_id}: {error_details}")
            raise
    
    def download_file(self, file_token: str) -> bytes:
        """下载文件内容"""
        endpoint = f"drive/v1/files/{file_token}/download"
        
        try:
            token = self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            url = f"{self.base_url}/{endpoint}"
            with httpx.Client() as client:
                response = client.get(url, headers=headers, timeout=30)
                response.raise_for_status()
            
            self.logger.info(f"Successfully downloaded file {file_token}")
            return response.content
        
        except Exception as e:
            self.logger.error(f"Error downloading file {file_token}: {e}")
            raise
    
    def get_bitable_tables(self, app_token: str) -> List[Dict[str, Any]]:
        """获取多维表格的表格列表"""
        endpoint = f"bitable/v1/apps/{app_token}/tables"
        
        try:
            result = self._make_request("GET", endpoint)
            tables = result.get("data", {}).get("items", [])
            self.logger.info(f"Successfully retrieved {len(tables)} tables from bitable {app_token}")
            return tables
        
        except Exception as e:
            self.logger.error(f"Error getting bitable tables for {app_token}: {e}")
            raise
    
    def get_bitable_records(self, app_token: str, table_id: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """获取多维表格记录"""
        endpoint = f"bitable/v1/apps/{app_token}/tables/{table_id}/records"
        params = {"page_size": page_size}
        
        try:
            result = self._make_request("GET", endpoint, params=params)
            records = result.get("data", {}).get("items", [])
            self.logger.info(f"Successfully retrieved {len(records)} records from table {table_id}")
            return records
        
        except Exception as e:
            self.logger.error(f"Error getting bitable records for {app_token}/{table_id}: {e}")
            raise
    
    def parse_document_content(self, document_id: str) -> Dict[str, Any]:
        """解析文档内容为结构化数据"""
        try:
            # 获取文档基本信息
            doc_info = self.get_document_info(document_id)
            
            # 尝试获取文档内容
            try:
                content_data = self.get_document_content(document_id)
            except Exception as content_error:
                self.logger.warning(f"Failed to get document content, using fallback mode: {content_error}")
                # 使用fallback模式，仅使用基本信息
                content_data = {
                    "fallback_mode": True,
                    "document": {"blocks": {}}
                }
            
            # 解析文档结构
            # 根据数据结构获取标题
            title = doc_info.get("title") or doc_info.get("file", {}).get("name") or "未命名文档"
            
            parsed_content = {
                "title": title,
                "document_id": document_id,
                "type": "document",
                "blocks": [],
                "images": [],
                "metadata": {
                    "created_time": doc_info.get("created_time"),
                    "modified_time": doc_info.get("modified_time"),
                    "owner_id": doc_info.get("owner_id"),
                    "size": doc_info.get("size", 0)
                },
                "fallback_mode": content_data.get("fallback_mode", False)
            }
            
            # 如果是fallback模式，创建一个基本的文本块
            if content_data.get("fallback_mode"):
                parsed_content["blocks"] = [{
                    "id": "fallback_block",
                    "type": "text",
                    "content": f"[由于权限限制，无法获取完整内容]\n\n文档标题: {parsed_content['title']}\n文档ID: {document_id}\n\n这是一个来自飞书的文档，请在飞书中查看完整内容。"
                }]
                self.logger.info(f"Used fallback mode for document {document_id}")
            else:
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
            
            self.logger.info(f"Successfully parsed document {document_id} with {len(parsed_content['blocks'])} blocks")
            return parsed_content
            
        except Exception as e:
            self.logger.error(f"Error parsing document content for {document_id}: {e}")
            raise
    
    def _parse_block(self, block_id: str, block_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析单个文档块"""
        try:
            block_type = block_data.get("block_type")
            
            if not block_type:
                return None
            
            parsed_block = {
                "id": block_id,
                "parent_id": block_data.get("parent_id"),
                "children": block_data.get("children", [])
            }
            
            # 根据块类型解析内容 (新的blocks API使用数字类型)
            if block_type == 1:  # 页面块
                parsed_block["type"] = "heading1"
                elements = block_data.get("page", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                parsed_block["level"] = 1
                
            elif block_type == 2:  # 文本块
                parsed_block["type"] = "text"
                elements = block_data.get("text", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                
            elif block_type == 3:  # 二级标题
                parsed_block["type"] = "heading2"
                elements = block_data.get("heading2", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                parsed_block["level"] = 2
                
            elif block_type == 5:  # 三级标题
                parsed_block["type"] = "heading3"
                elements = block_data.get("heading3", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                parsed_block["level"] = 3
                
            elif block_type == 14:  # 代码块
                parsed_block["type"] = "code"
                elements = block_data.get("code", {}).get("elements", [])
                parsed_block["content"] = self._parse_text_elements(elements)
                style = block_data.get("code", {}).get("style", {})
                parsed_block["language"] = self._get_language_from_id(style.get("language", 0))
                
            elif block_type == 27:  # 图片块
                parsed_block["type"] = "image"
                image_data = block_data.get("image", {})
                parsed_block["file_token"] = image_data.get("token", "")
                parsed_block["alt_text"] = f"图片 ({image_data.get('width', 0)}x{image_data.get('height', 0)})"
                parsed_block["content"] = f"[图片: {parsed_block['file_token']}]"
                
            elif block_type in ["text", "heading1", "heading2", "heading3"]:  # 兼容旧格式
                parsed_block["type"] = block_type
                if block_type == "text":
                    text_run = block_data.get("text", {}).get("elements", [])
                    parsed_block["content"] = self._parse_text_elements(text_run)
                elif block_type == "heading1":
                    elements = block_data.get("heading1", {}).get("elements", [])
                    parsed_block["content"] = self._parse_text_elements(elements)
                    parsed_block["level"] = 1
                elif block_type == "heading2":
                    elements = block_data.get("heading2", {}).get("elements", [])
                    parsed_block["content"] = self._parse_text_elements(elements)
                    parsed_block["level"] = 2
                elif block_type == "heading3":
                    elements = block_data.get("heading3", {}).get("elements", [])
                    parsed_block["content"] = self._parse_text_elements(elements)
                    parsed_block["level"] = 3
            else:
                # 未知类型，记录并跳过
                self.logger.warning(f"Unknown block type {block_type} for block {block_id}")
                return None
                
            return parsed_block
            
        except Exception as e:
            self.logger.error(f"Error parsing block {block_id}: {e}")
            return None
    
    def _get_language_from_id(self, language_id: int) -> str:
        """根据语言ID获取语言名称"""
        language_map = {
            0: "plain_text",
            1: "python",
            2: "java",
            3: "cpp",
            4: "c",
            5: "csharp",
            6: "javascript",
            7: "bash",
            8: "shell",
            9: "go",
            10: "php",
            11: "ruby",
            12: "swift",
            13: "kotlin",
            14: "rust",
            15: "typescript",
            16: "html",
            17: "css",
            18: "scss",
            19: "less",
            20: "xml",
            21: "json",
            22: "yaml",
            23: "toml",
            24: "ini",
            25: "dockerfile",
            26: "makefile",
            27: "cmake",
            28: "sql",
            29: "markdown",
            30: "latex",
            31: "r",
            32: "matlab",
            33: "scala",
            34: "perl",
            35: "lua",
            36: "dart",
            37: "vim",
            38: "apache",
            39: "nginx",
            40: "powershell",
            41: "batch",
            42: "asm",
            43: "pascal",
            44: "fortran",
            45: "cobol",
            46: "prolog",
            47: "haskell",
            48: "scheme",
            49: "bash"  # 重复但保留
        }
        return language_map.get(language_id, "plain_text")
    
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
            # 新的blocks API直接包含text_run
            if "text_run" in element:
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
                if text_style.get("inline_code"):
                    content = f"`{content}`"
                
                content_parts.append(content)
            # 兼容旧格式
            elif element.get("type") == "text_run":
                text_run = element.get("text_run", {})
                content = text_run.get("content", "")
                content_parts.append(content)
        
        return "".join(content_parts)
    
    def get_image_download_url(self, file_token: str) -> str:
        """获取图片下载链接"""
        try:
            token = self._get_access_token()
            download_url = f"{self.base_url}/drive/v1/files/{file_token}/download"
            
            self.logger.info(f"Generated download URL for image {file_token}")
            return download_url
            
        except Exception as e:
            self.logger.error(f"Error generating download URL for image {file_token}: {e}")
            raise
    
    def get_folder_documents_with_cache(self, folder_token: str, use_cache: bool = True, 
                                      max_depth: int = 5) -> List[Dict[str, Any]]:
        """获取文件夹文档，支持缓存以减少API调用"""
        cache_key = f"folder_docs_{folder_token}_{max_depth}"
        
        # 简单的内存缓存（生产环境建议使用Redis）
        if not hasattr(self, '_folder_cache'):
            self._folder_cache = {}
            
        if use_cache and cache_key in self._folder_cache:
            cache_data = self._folder_cache[cache_key]
            # 检查缓存是否过期（10分钟）
            if time.time() - cache_data['timestamp'] < 600:
                self.logger.info(f"Using cached data for folder {folder_token}")
                return cache_data['documents']
        
        # 获取文档列表
        try:
            documents = self.get_all_folder_documents(folder_token, max_depth)
            
            # 缓存结果
            self._folder_cache[cache_key] = {
                'documents': documents,
                'timestamp': time.time()
            }
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Error getting folder documents with cache: {e}")
            # 如果有缓存，返回缓存数据
            if cache_key in self._folder_cache:
                self.logger.warning(f"API failed, returning cached data for folder {folder_token}")
                return self._folder_cache[cache_key]['documents']
            else:
                raise
    
    
    def get_all_folder_documents(self, folder_token: str, max_depth: int = 10) -> List[Dict[str, Any]]:
        """递归获取文件夹及其子文件夹中的所有文档，带有API限流和深度限制"""
        all_docs = []
        visited_folders = set()  # 防止循环引用
        self._get_all_folder_documents_recursive(folder_token, all_docs, visited_folders, 0, max_depth)
        self.logger.info(f"Retrieved total {len(all_docs)} documents from root folder {folder_token}")
        return all_docs

    def _get_all_folder_documents_recursive(self, folder_token: str, all_docs: List[Dict[str, Any]], 
                                          visited_folders: set, current_depth: int, max_depth: int):
        """递归辅助函数，带有深度限制和重复检测"""
        
        # 检查递归深度限制
        if current_depth >= max_depth:
            self.logger.warning(f"Reached maximum depth {max_depth} for folder {folder_token}")
            return
            
        # 检查是否已访问过此文件夹（防止循环引用）
        if folder_token in visited_folders:
            self.logger.warning(f"Folder {folder_token} already visited, skipping to prevent loop")
            return
            
        visited_folders.add(folder_token)
        page_token = None
        
        while True:
            try:
                # 添加延时以减少API调用频率
                time.sleep(0.1)  # 100ms延时
                
                data = self.list_files_in_folder(folder_token, page_token=page_token)
                files = data.get("files", [])
                
                for item in files:
                    item_type = item.get("type")
                    if item_type == 'folder':
                        # 如果是文件夹，递归进入
                        self._get_all_folder_documents_recursive(
                            item.get("token"), all_docs, visited_folders, current_depth + 1, max_depth
                        )
                    elif item_type in ["docx", "doc", "sheet", "bitable"]:
                        # 如果是支持的文档类型，添加到列表
                        all_docs.append({
                            "token": item.get("token"),
                            "name": item.get("name"),
                            "type": item_type,
                            "url": item.get("url"),
                            "created_time": item.get("created_time"),
                            "modified_time": item.get("modified_time"),
                            "owner_id": item.get("owner_id"),
                            "size": item.get("size", 0),
                            "folder_path": folder_token  # 记录所在文件夹
                        })

                # 检查分页信息
                if data.get("has_more") and data.get("page_token"):
                    page_token = data.get("page_token")
                    self.logger.info(f"Found more pages for folder {folder_token}, next page_token: {page_token[:10]}...")
                else:
                    # 如果没有更多页面或page_token为空，退出循环
                    break
                    
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    self.logger.error(f"API rate limit exceeded for folder {folder_token}: {e}")
                    # API限流时，等待更长时间后重试
                    time.sleep(5)
                    try:
                        # 重试一次，保持相同的page_token
                        data = self.list_files_in_folder(folder_token, page_token=page_token)
                        files = data.get("files", [])
                        
                        # 处理重试后的文件
                        for item in files:
                            item_type = item.get("type")
                            if item_type == 'folder':
                                self._get_all_folder_documents_recursive(
                                    item.get("token"), all_docs, visited_folders, current_depth + 1, max_depth
                                )
                            elif item_type in ["docx", "doc", "sheet", "bitable"]:
                                all_docs.append({
                                    "token": item.get("token"),
                                    "name": item.get("name"),
                                    "type": item_type,
                                    "url": item.get("url"),
                                    "created_time": item.get("created_time"),
                                    "modified_time": item.get("modified_time"),
                                    "owner_id": item.get("owner_id"),
                                    "size": item.get("size", 0),
                                    "folder_path": folder_token
                                })
                        
                        # 检查重试后的分页信息
                        if data.get("has_more") and data.get("page_token"):
                            page_token = data.get("page_token")
                        else:
                            break
                            
                    except Exception as retry_e:
                        self.logger.error(f"Retry failed for folder {folder_token}: {retry_e}")
                        break
                else:
                    self.logger.error(f"Error processing folder {folder_token}: {e}")
                    break