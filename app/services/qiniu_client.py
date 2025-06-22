"""
Qiniu Cloud storage client for image handling
"""
import hashlib
import os
import tempfile
from io import BytesIO
from typing import Tuple, Optional
import logging
from PIL import Image
import requests

try:
    from qiniu import Auth, put_data, put_file, BucketManager
except ImportError:
    logging.warning("qiniu package not installed, QiniuClient will have limited functionality")
    Auth = None

from config import settings

logger = logging.getLogger(__name__)


class QiniuClient:
    """七牛云存储客户端"""
    
    def __init__(self):
        self.access_key = settings.qiniu_access_key
        self.secret_key = settings.qiniu_secret_key
        self.bucket_name = settings.qiniu_bucket
        self.cdn_domain = settings.qiniu_cdn_domain
        
        if Auth:
            self.auth = Auth(self.access_key, self.secret_key)
            self.bucket_manager = BucketManager(self.auth)
        else:
            self.auth = None
            self.bucket_manager = None
            logger.warning("Qiniu SDK not available, using fallback methods")
    
    def _generate_file_hash(self, data: bytes) -> str:
        """生成文件MD5哈希"""
        return hashlib.md5(data).hexdigest()
    
    def _compress_image(self, image_data: bytes, quality: int = 70, format_type: str = "WEBP") -> bytes:
        """压缩图片"""
        try:
            # 打开图片
            image = Image.open(BytesIO(image_data))
            
            # 转换为RGB模式（WEBP需要）
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            
            # 压缩图片
            output = BytesIO()
            image.save(output, format=format_type, quality=quality, optimize=True)
            compressed_data = output.getvalue()
            
            compression_ratio = len(compressed_data) / len(image_data)
            logger.info(f"Image compressed: {len(image_data)} -> {len(compressed_data)} bytes (ratio: {compression_ratio:.2f})")
            
            return compressed_data
        
        except Exception as e:
            logger.error(f"Error compressing image: {e}")
            # 如果压缩失败，返回原图片
            return image_data
    
    def _generate_filename(self, file_hash: str, extension: str = "webp") -> str:
        """生成文件名"""
        return f"images/{file_hash}.{extension}"
    
    def upload_image(self, image_data: bytes, filename: Optional[str] = None, compress: bool = True) -> Tuple[str, str, int]:
        """
        上传图片到七牛云
        
        Args:
            image_data: 图片二进制数据
            filename: 自定义文件名（可选）
            compress: 是否压缩图片
        
        Returns:
            Tuple[CDN链接, 文件哈希, 文件大小]
        """
        try:
            # 压缩图片
            if compress:
                processed_data = self._compress_image(image_data)
            else:
                processed_data = image_data
            
            # 生成文件哈希
            file_hash = self._generate_file_hash(processed_data)
            
            # 生成文件名
            if not filename:
                filename = self._generate_filename(file_hash)
            
            # 检查文件是否已存在
            if self._file_exists(filename):
                cdn_url = f"{self.cdn_domain.rstrip('/')}/{filename}"
                logger.info(f"File already exists: {cdn_url}")
                return cdn_url, file_hash, len(processed_data)
            
            # 上传文件
            if self.auth:
                token = self.auth.upload_token(self.bucket_name, filename)
                ret, info = put_data(token, filename, processed_data)
                
                if info.status_code == 200:
                    cdn_url = f"{self.cdn_domain.rstrip('/')}/{filename}"
                    logger.info(f"Successfully uploaded image to: {cdn_url}")
                    return cdn_url, file_hash, len(processed_data)
                else:
                    logger.error(f"Failed to upload image: {info}")
                    raise Exception(f"Upload failed: {info}")
            else:
                # 降级处理：保存到本地
                local_path = f"static/images/{filename}"
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(processed_data)
                
                cdn_url = f"/static/images/{filename}"
                logger.info(f"Saved image locally: {cdn_url}")
                return cdn_url, file_hash, len(processed_data)
        
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            raise
    
    def _file_exists(self, filename: str) -> bool:
        """检查文件是否存在"""
        if not self.bucket_manager:
            return False
        
        try:
            ret, info = self.bucket_manager.stat(self.bucket_name, filename)
            return info.status_code == 200
        except Exception:
            return False
    
    def download_and_upload_image(self, image_url: str, compress: bool = True) -> Tuple[str, str, int]:
        """
        从URL下载图片并上传到七牛云
        
        Args:
            image_url: 图片URL
            compress: 是否压缩图片
        
        Returns:
            Tuple[CDN链接, 文件哈希, 文件大小]
        """
        try:
            # 下载图片
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            image_data = response.content
            logger.info(f"Downloaded image from {image_url}, size: {len(image_data)} bytes")
            
            # 上传到七牛云
            return self.upload_image(image_data, compress=compress)
        
        except Exception as e:
            logger.error(f"Error downloading and uploading image from {image_url}: {e}")
            raise
    
    def delete_file(self, filename: str) -> bool:
        """删除文件"""
        if not self.bucket_manager:
            logger.warning("Bucket manager not available")
            return False
        
        try:
            ret, info = self.bucket_manager.delete(self.bucket_name, filename)
            if info.status_code == 200:
                logger.info(f"Successfully deleted file: {filename}")
                return True
            else:
                logger.error(f"Failed to delete file {filename}: {info}")
                return False
        
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return False
    
    def get_file_info(self, filename: str) -> Optional[dict]:
        """获取文件信息"""
        if not self.bucket_manager:
            return None
        
        try:
            ret, info = self.bucket_manager.stat(self.bucket_name, filename)
            if info.status_code == 200:
                return ret
            else:
                return None
        
        except Exception as e:
            logger.error(f"Error getting file info for {filename}: {e}")
            return None
    
    def list_files(self, prefix: str = "", limit: int = 100) -> list:
        """列出文件"""
        if not self.bucket_manager:
            return []
        
        try:
            ret, eof, info = self.bucket_manager.list(self.bucket_name, prefix=prefix, limit=limit)
            if info.status_code == 200:
                return ret.get('items', [])
            else:
                logger.error(f"Failed to list files: {info}")
                return []
        
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def download_from_feishu_and_upload(self, feishu_client, file_token: str, compress: bool = True) -> Tuple[str, str, int]:
        """
        从飞书下载图片并上传到七牛云
        
        Args:
            feishu_client: 飞书客户端实例
            file_token: 飞书文件token
            compress: 是否压缩图片
        
        Returns:
            Tuple[CDN链接, 文件哈希, 文件大小]
        """
        try:
            # 从飞书下载图片
            image_data = feishu_client.download_file(file_token)
            logger.info(f"Downloaded image from Feishu file_token: {file_token}, size: {len(image_data)} bytes")
            
            # 上传到七牛云
            return self.upload_image(image_data, compress=compress)
            
        except Exception as e:
            logger.error(f"Error downloading from Feishu and uploading file_token {file_token}: {e}")
            raise
    
    def process_feishu_images(self, feishu_client, images: list) -> dict:
        """
        批量处理飞书图片
        
        Args:
            feishu_client: 飞书客户端实例
            images: 图片信息列表，包含file_token等
        
        Returns:
            图片映射字典 {file_token: cdn_url}
        """
        image_mappings = {}
        
        for image in images:
            file_token = image.get("file_token")
            if not file_token:
                continue
            
            try:
                cdn_url, file_hash, file_size = self.download_from_feishu_and_upload(
                    feishu_client, file_token
                )
                
                image_mappings[file_token] = {
                    "cdn_url": cdn_url,
                    "file_hash": file_hash,
                    "file_size": file_size,
                    "alt_text": image.get("alt_text", "")
                }
                
                logger.info(f"Successfully processed Feishu image {file_token} -> {cdn_url}")
                
            except Exception as e:
                logger.error(f"Failed to process Feishu image {file_token}: {e}")
                # 添加错误信息到映射中
                image_mappings[file_token] = {
                    "error": str(e),
                    "cdn_url": None
                }
        
        return image_mappings
    
    def get_storage_stats(self) -> dict:
        """获取存储统计信息"""
        try:
            files = self.list_files(prefix="images/", limit=1000)
            
            total_files = len(files)
            total_size = sum(file.get('fsize', 0) for file in files)
            
            stats = {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "average_size_bytes": round(total_size / total_files, 2) if total_files > 0 else 0
            }
            
            logger.info(f"Storage stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "average_size_bytes": 0
            }