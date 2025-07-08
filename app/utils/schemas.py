#!/usr/bin/env python3
"""
输入验证模式 - 使用marshmallow定义API输入验证规则
"""
from marshmallow import Schema, fields, validate, ValidationError


class SyncConfigSchema(Schema):
    """同步配置验证模式"""
    platform = fields.Str(required=True, validate=validate.OneOf(['feishu', 'notion']))
    document_id = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    sync_direction = fields.Str(required=True, validate=validate.OneOf(['bidirectional', 'feishu_to_notion']))
    is_sync_enabled = fields.Bool(load_default=True)
    auto_sync = fields.Bool(load_default=True)
    webhook_url = fields.Str(validate=validate.Length(max=500), allow_none=True)


class BatchSyncSchema(Schema):
    """批量同步验证模式"""
    document_ids = fields.List(
        fields.Str(validate=validate.Length(min=1, max=100)), 
        required=True, 
        validate=validate.Length(min=1, max=50)
    )
    force_sync = fields.Bool(load_default=False)


class BatchDeleteSchema(Schema):
    """批量删除验证模式"""
    record_ids = fields.List(fields.Int(), validate=validate.Length(min=1, max=100))
    status = fields.Str(validate=validate.OneOf(['failed', 'completed', 'pending']))


class BatchRetrySchema(Schema):
    """批量重试验证模式"""
    record_ids = fields.List(fields.Int(), validate=validate.Length(min=1, max=100))
    retry_failed_only = fields.Bool(load_default=True)


class URLParseSchema(Schema):
    """URL解析验证模式"""
    urls = fields.List(
        fields.Str(validate=validate.Length(min=1, max=1000)), 
        required=True, 
        validate=validate.Length(min=1, max=20)
    )
    url = fields.Str(validate=validate.Length(min=1, max=1000))  # 向后兼容


class ManualSyncSchema(Schema):
    """手动同步验证模式"""
    document_ids = fields.List(
        fields.Str(validate=validate.Length(min=1, max=100)), 
        required=True, 
        validate=validate.Length(min=1, max=20)
    )
    source_platform = fields.Str(required=True, validate=validate.OneOf(['feishu', 'notion']))
    target_platform = fields.Str(required=True, validate=validate.OneOf(['feishu', 'notion']))
    force_resync = fields.Bool(load_default=False)


class FolderScanSchema(Schema):
    """文件夹扫描验证模式"""
    folder_path = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    max_depth = fields.Int(load_default=2, validate=validate.Range(min=1, max=5))
    use_cache = fields.Bool(load_default=True)


class ConfigUpdateSchema(Schema):
    """配置更新验证模式"""
    is_sync_enabled = fields.Bool()
    auto_sync = fields.Bool()
    webhook_url = fields.Str(validate=validate.Length(max=500), allow_none=True)
    sync_direction = fields.Str(validate=validate.OneOf(['bidirectional', 'feishu_to_notion']))


class PaginationSchema(Schema):
    """分页参数验证模式"""
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    limit = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    
    
class FilterSchema(Schema):
    """过滤参数验证模式"""
    status = fields.Str(validate=validate.OneOf(['pending', 'processing', 'success', 'failed', 'completed']))
    platform = fields.Str(validate=validate.OneOf(['feishu', 'notion']))
    start_date = fields.DateTime()
    end_date = fields.DateTime()


class SearchSchema(Schema):
    """搜索参数验证模式"""
    query = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    search_type = fields.Str(validate=validate.OneOf(['all', 'configs', 'records', 'documents']))
    limit = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))


# 自定义验证器
def validate_document_id(value):
    """验证文档ID格式"""
    if not value or not isinstance(value, str):
        raise ValidationError('文档ID必须是非空字符串')
    
    # 移除空格
    value = value.strip()
    if len(value) < 1:
        raise ValidationError('文档ID不能为空')
    
    if len(value) > 100:
        raise ValidationError('文档ID长度不能超过100个字符')
    
    return value


def validate_sync_platforms(source, target):
    """验证同步平台组合"""
    valid_platforms = ['feishu', 'notion']
    
    if source not in valid_platforms:
        raise ValidationError(f'无效的源平台: {source}')
    
    if target not in valid_platforms:
        raise ValidationError(f'无效的目标平台: {target}')
    
    if source == target:
        raise ValidationError('源平台和目标平台不能相同')
    
    return True


def validate_batch_size(items, max_size=50):
    """验证批量操作的大小"""
    if not items:
        raise ValidationError('批量操作列表不能为空')
    
    if len(items) > max_size:
        raise ValidationError(f'单次批量操作最多支持{max_size}个项目')
    
    return True


# 组合验证模式
class CompleteConfigSchema(SyncConfigSchema):
    """完整的配置验证模式（包含更新字段）"""
    platform = fields.Str(validate=validate.OneOf(['feishu', 'notion']))
    document_id = fields.Str(validate=validate.Length(min=1, max=100))
    sync_direction = fields.Str(validate=validate.OneOf(['bidirectional', 'feishu_to_notion']))


class CompleteRecordSchema(Schema):
    """完整的记录验证模式"""
    source_platform = fields.Str(required=True, validate=validate.OneOf(['feishu', 'notion']))
    target_platform = fields.Str(required=True, validate=validate.OneOf(['feishu', 'notion']))
    source_id = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    target_id = fields.Str(validate=validate.Length(min=1, max=100), allow_none=True)
    content_type = fields.Str(validate=validate.OneOf(['document', 'folder', 'sheet']))
    sync_status = fields.Str(validate=validate.OneOf(['pending', 'processing', 'success', 'failed']))


# 导出常用的验证函数
def get_schema_by_name(schema_name):
    """根据名称获取验证模式"""
    schemas = {
        'sync_config': SyncConfigSchema,
        'batch_sync': BatchSyncSchema,
        'batch_delete': BatchDeleteSchema,
        'batch_retry': BatchRetrySchema,
        'url_parse': URLParseSchema,
        'manual_sync': ManualSyncSchema,
        'folder_scan': FolderScanSchema,
        'config_update': ConfigUpdateSchema,
        'pagination': PaginationSchema,
        'filter': FilterSchema,
        'search': SearchSchema,
    }
    
    return schemas.get(schema_name)