#!/usr/bin/env python3
"""
工具函数模块 - 提供各种实用的辅助函数
"""
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional


def get_beijing_time() -> datetime:
    """获取北京时间"""
    # 创建北京时区 (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)


def get_beijing_time_str() -> str:
    """获取北京时间字符串格式"""
    return get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')


def utc_to_beijing(utc_dt: datetime) -> datetime:
    """将UTC时间转换为北京时间"""
    if utc_dt.tzinfo is None:
        # 如果没有时区信息，假设是UTC
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    # 转换为北京时间
    beijing_tz = timezone(timedelta(hours=8))
    return utc_dt.astimezone(beijing_tz)


def beijing_to_utc(beijing_dt: datetime) -> datetime:
    """将北京时间转换为UTC时间"""
    if beijing_dt.tzinfo is None:
        # 如果没有时区信息，假设是北京时间
        beijing_tz = timezone(timedelta(hours=8))
        beijing_dt = beijing_dt.replace(tzinfo=beijing_tz)
    
    # 转换为UTC
    return beijing_dt.astimezone(timezone.utc)


def format_datetime(dt: datetime = None) -> str:
    """统一日期时间格式处理（转换为北京时间）"""
    if isinstance(dt, str):
        return dt
    elif isinstance(dt, datetime):
        # 将UTC时间转换为北京时间
        beijing_dt = utc_to_beijing(dt)
        return beijing_dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        # 返回当前北京时间
        return get_beijing_time_str()


def safe_row_to_dict(row, default_values: Dict = None) -> Dict:
    """安全地将数据库行转换为字典，处理None值"""
    if row is None:
        return default_values or {}
    
    result = dict(row)
    
    # 处理日期时间字段
    for key, value in result.items():
        if key in ['created_at', 'updated_at', 'last_sync_time'] and value:
            try:
                # 如果是ISO格式的字符串，转换为标准格式
                if isinstance(value, str) and 'T' in value:
                    # 处理带微秒的ISO格式
                    if '.' in value:
                        # 截断微秒到6位，然后移除微秒部分
                        value = value.split('.')[0]
                    
                    # 移除时区信息
                    value = value.replace('Z', '').replace('+00:00', '')
                    
                    try:
                        dt = datetime.fromisoformat(value)
                        # 转换为北京时间
                        beijing_dt = utc_to_beijing(dt)
                        result[key] = beijing_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        # 尝试手动解析
                        dt = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
                        # 转换为北京时间
                        beijing_dt = utc_to_beijing(dt)
                        result[key] = beijing_dt.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, datetime):
                    # 转换为北京时间
                    beijing_dt = utc_to_beijing(value)
                    result[key] = beijing_dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, AttributeError) as e:
                # 如果转换失败，输出警告但保持原值
                print(f"Warning: Failed to parse datetime '{value}': {e}")
                pass
    
    # 如果提供了默认值，合并它们
    if default_values:
        for key, default_value in default_values.items():
            if key not in result or result[key] is None:
                result[key] = default_value
    
    return result


def generate_record_number() -> str:
    """生成唯一记录编号"""
    import uuid
    # 使用更高精度的时间戳和UUID的一部分确保唯一性
    timestamp = int(time.time() * 1000)  # 毫秒级时间戳
    uuid_suffix = str(uuid.uuid4())[:8]  # UUID前8位
    return f"{timestamp}_{uuid_suffix}"


def paginate_query(base_query: str, page: int = 1, per_page: int = 20, max_per_page: int = 100) -> Dict[str, Any]:
    """统一分页处理"""
    # 注意：此函数已废弃，请使用SQLAlchemy的直接分页功能
    # 如：session.query(Model).offset((page-1)*per_page).limit(per_page).all()
    
    per_page = min(per_page, max_per_page)
    offset = (page - 1) * per_page
    
    # 这是一个向后兼容的实现，建议迁移到SQLAlchemy分页
    from database.connection import db
    from sqlalchemy import text
    
    with db.get_session() as session:
        # 获取总数
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        total = session.execute(text(count_query)).scalar()
        
        # 获取分页数据
        paginated_query = f"{base_query} LIMIT {per_page} OFFSET {offset}"
        result = session.execute(text(paginated_query))
        items = [dict(row) for row in result]
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'limit': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    }


def validate_platform(platform: str) -> bool:
    """验证平台类型是否有效"""
    valid_platforms = ['feishu', 'notion']
    return platform in valid_platforms


def validate_sync_direction(direction: str) -> bool:
    """验证同步方向是否有效"""
    valid_directions = ['bidirectional', 'feishu_to_notion']
    return direction in valid_directions


def validate_sync_status(status: str) -> bool:
    """验证同步状态是否有效"""
    valid_statuses = ['pending', 'processing', 'success', 'failed', 'completed']
    return status in valid_statuses


def clean_document_id(doc_id: str) -> str:
    """清理文档ID，移除不必要的字符"""
    if not doc_id:
        return ""
    
    # 移除前后空格
    doc_id = doc_id.strip()
    
    # 移除可能的URL参数
    if '?' in doc_id:
        doc_id = doc_id.split('?')[0]
    
    # 移除可能的锚点
    if '#' in doc_id:
        doc_id = doc_id.split('#')[0]
    
    return doc_id


def extract_error_code(error_message: str) -> str:
    """从错误消息中提取错误代码"""
    if not error_message:
        return "UNKNOWN_ERROR"
    
    error_msg = error_message.lower()
    
    if "401" in error_msg or "unauthorized" in error_msg:
        return "AUTHENTICATION_FAILED"
    elif "403" in error_msg or "forbidden" in error_msg:
        return "PERMISSION_DENIED"
    elif "404" in error_msg or "not found" in error_msg:
        return "RESOURCE_NOT_FOUND"
    elif "429" in error_msg or "too many requests" in error_msg:
        return "RATE_LIMIT_EXCEEDED"
    elif "timeout" in error_msg:
        return "TIMEOUT_ERROR"
    elif "network" in error_msg or "connection" in error_msg:
        return "NETWORK_ERROR"
    else:
        return "UNKNOWN_ERROR"


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本到指定长度"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def parse_feishu_url(url: str) -> Optional[Dict[str, str]]:
    """解析飞书URL，提取文档信息"""
    if not url or not ('feishu' in url or 'larksuite' in url):
        return None
    
    try:
        # 提取文档ID
        if '/docs/' in url:
            doc_id = url.split('/docs/')[-1].split('?')[0].split('#')[0]
            doc_type = 'docs'
        elif '/folder/' in url:
            doc_id = url.split('/folder/')[-1].split('?')[0].split('#')[0]
            doc_type = 'folder'
        elif '/sheets/' in url:
            doc_id = url.split('/sheets/')[-1].split('?')[0].split('#')[0]
            doc_type = 'sheets'
        else:
            # 尝试从URL末尾提取ID
            doc_id = url.split('/')[-1].split('?')[0].split('#')[0] if '/' in url else url
            doc_type = 'unknown'
        
        if doc_id:
            return {
                'platform': 'feishu',
                'document_id': clean_document_id(doc_id),
                'document_type': doc_type,
                'original_url': url
            }
    except Exception:
        pass
    
    return None


def parse_notion_url(url: str) -> Optional[Dict[str, str]]:
    """解析Notion URL，提取页面信息"""
    if not url or 'notion' not in url:
        return None
    
    try:
        # Notion URL通常格式为: https://www.notion.so/page-title-id
        doc_id = url.split('/')[-1].split('?')[0].split('#')[0] if '/' in url else url
        
        if doc_id:
            return {
                'platform': 'notion',
                'document_id': clean_document_id(doc_id),
                'document_type': 'page',
                'original_url': url
            }
    except Exception:
        pass
    
    return None


def calculate_success_rate(total: int, successful: int) -> float:
    """计算成功率"""
    if total == 0:
        return 0.0
    return round((successful / total) * 100, 2)


def is_valid_email(email: str) -> bool:
    """简单的邮箱格式验证"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """掩码敏感数据"""
    if not data or len(data) <= visible_chars:
        return data
    
    visible_start = visible_chars // 2
    visible_end = visible_chars - visible_start
    
    masked_middle = mask_char * (len(data) - visible_chars)
    
    return data[:visible_start] + masked_middle + data[-visible_end:] if visible_end > 0 else data[:visible_start] + masked_middle