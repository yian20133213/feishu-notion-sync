#!/usr/bin/env python3
"""
装饰器模块 - 提供各种用于API的装饰器
"""
from functools import wraps
from flask import request, jsonify, g
from marshmallow import ValidationError
import hashlib
import secrets
from datetime import datetime


# API密钥管理
API_KEYS = {
    'default': hashlib.sha256('sync_system_2024'.encode()).hexdigest()[:32]
}


class APIResponse:
    """统一API响应格式"""
    
    @staticmethod
    def success(data=None, meta=None):
        """成功响应"""
        response = {
            "success": True,
            "data": data,
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "version": "v1",
                **(meta or {})
            }
        }
        return jsonify(response)
    
    @staticmethod
    def error(message, code="UNKNOWN_ERROR", details=None, status_code=400):
        """错误响应"""
        response = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details
            },
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "request_id": secrets.token_hex(8)
            }
        }
        return jsonify(response), status_code


def validate_json(required_fields=None):
    """JSON输入验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json and request.method in ['POST', 'PUT', 'PATCH']:
                return APIResponse.error("请求必须是JSON格式", "INVALID_CONTENT_TYPE", status_code=400)
            
            data = request.get_json() or {}
            
            # 检查必需字段
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return APIResponse.error(
                        f"缺少必需字段: {', '.join(missing_fields)}", 
                        "MISSING_REQUIRED_FIELDS", 
                        details={"missing_fields": missing_fields},
                        status_code=400
                    )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_input(schema_class):
    """输入验证装饰器（使用marshmallow）"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json and request.method in ['POST', 'PUT', 'PATCH']:
                return APIResponse.error("请求必须是JSON格式", "INVALID_CONTENT_TYPE", status_code=400)
            
            try:
                schema = schema_class()
                data = schema.load(request.get_json() or {})
                # 将验证后的数据存储在 g 对象中
                g.validated_data = data
                return f(*args, **kwargs)
            except ValidationError as err:
                return APIResponse.error(
                    "输入数据验证失败", 
                    "VALIDATION_ERROR", 
                    details=err.messages, 
                    status_code=400
                )
        return decorated_function
    return decorator


def require_api_key(f):
    """API密钥验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key not in API_KEYS.values():
            return APIResponse.error(
                "无效或缺失的API密钥", 
                "UNAUTHORIZED", 
                status_code=401
            )
        return f(*args, **kwargs)
    return decorated_function


def paginated(max_per_page=100):
    """分页装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                page = int(request.args.get('page', 1))
                per_page = min(int(request.args.get('limit', 20)), max_per_page)
                if page < 1 or per_page < 1:
                    return APIResponse.error("页码和每页数量必须大于0", "INVALID_PAGINATION", status_code=400)
                # 将分页信息存储在 g 对象中
                g.pagination = {'page': page, 'per_page': per_page}
                return f(*args, **kwargs)
            except ValueError:
                return APIResponse.error("页码和每页数量必须是有效数字", "INVALID_PAGINATION", status_code=400)
        return decorated_function
    return decorator


def rate_limit(requests_per_minute=60):
    """简单的速率限制装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 这里可以实现基于IP或用户的速率限制
            # 当前为占位符实现
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_api_call(f):
    """API调用日志装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import current_app
        start_time = datetime.now()
        
        try:
            result = f(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            current_app.logger.info(
                f"API调用: {request.method} {request.path} - "
                f"状态: 成功 - 耗时: {duration:.3f}s"
            )
            return result
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            current_app.logger.error(
                f"API调用: {request.method} {request.path} - "
                f"状态: 失败({str(e)}) - 耗时: {duration:.3f}s"
            )
            raise
    return decorated_function


def cache_response(timeout=300):
    """响应缓存装饰器（简单实现）"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 这里可以实现基于Redis或内存的缓存
            # 当前为占位符实现
            return f(*args, **kwargs)
        return decorated_function
    return decorator