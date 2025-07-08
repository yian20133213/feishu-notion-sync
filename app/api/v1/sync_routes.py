#!/usr/bin/env python3
"""
同步相关API路由 - 处理同步记录和操作
"""
from flask import request, current_app
from app.utils import APIResponse, validate_json, paginated
from app.services import SyncService, DocumentService


def register_routes(bp):
    """注册同步相关路由到蓝图"""
    
    @bp.route('/sync/records', methods=['GET'])
    @paginated(max_per_page=100)
    def get_sync_records():
        """获取同步记录列表（支持状态过滤）"""
        try:
            # 获取过滤参数
            status = request.args.get('status')
            platform = request.args.get('platform')
            
            from flask import g
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.get_sync_records(
                page=g.pagination['page'], 
                per_page=g.pagination['per_page'],
                status=status,
                platform=platform
            )
            return APIResponse.success(result)
            
        except Exception as e:
            return APIResponse.error(f"获取记录列表失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/records/batch', methods=['POST'])
    @validate_json(['document_ids'])
    def create_batch_sync_records():
        """统一的批量同步接口"""
        try:
            data = request.get_json()
            document_ids = data.get('document_ids', [])
            force_sync = data.get('force_sync', False)
            
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.create_sync_records_batch(document_ids, force_sync)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "VALIDATION_ERROR", status_code=400)
        except Exception as e:
            return APIResponse.error(f"创建同步任务失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/records/batch', methods=['DELETE'])
    @validate_json()
    def delete_sync_records_batch():
        """统一的批量删除接口"""
        try:
            data = request.get_json()
            record_ids = data.get('record_ids', [])
            status = data.get('status')
            
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.delete_sync_records_batch(record_ids, status)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "VALIDATION_ERROR", status_code=400)
        except Exception as e:
            return APIResponse.error(f"批量删除失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/records/batch', methods=['PATCH'])
    @validate_json()
    def retry_sync_records_batch():
        """统一的批量重试接口"""
        try:
            data = request.get_json()
            record_ids = data.get('record_ids', [])
            retry_failed_only = data.get('retry_failed_only', True)
            
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.retry_sync_records_batch(record_ids, retry_failed_only)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "VALIDATION_ERROR", status_code=400)
        except Exception as e:
            return APIResponse.error(f"批量重试失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/records/<int:record_id>', methods=['PATCH'])
    def retry_sync_record(record_id):
        """重试单个同步任务"""
        try:
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.retry_sync_record(record_id)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "RECORD_NOT_FOUND", status_code=404)
        except Exception as e:
            return APIResponse.error(f"重试失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/records/<int:record_id>', methods=['DELETE'])
    def delete_sync_record(record_id):
        """删除单个同步记录"""
        try:
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.delete_sync_record(record_id)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "RECORD_NOT_FOUND", status_code=404)
        except Exception as e:
            return APIResponse.error(f"删除失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/records/<int:record_id>', methods=['GET'])
    def get_sync_record_detail(record_id):
        """获取单个同步记录详情"""
        try:
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.get_sync_record_detail(record_id)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "RECORD_NOT_FOUND", status_code=404)
        except Exception as e:
            return APIResponse.error(f"获取详情失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/sync/trigger', methods=['POST'])
    @validate_json(['document_id'])
    def trigger_sync():
        """触发单个文档同步"""
        try:
            data = request.get_json()
            document_id = data.get('document_id')
            
            document_service = DocumentService(logger=current_app.logger)
            result = document_service.trigger_single_sync(document_id)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "VALIDATION_ERROR", status_code=400)
        except Exception as e:
            return APIResponse.error(f"触发同步失败: {str(e)}", "TRIGGER_SYNC_ERROR", status_code=500)

    @bp.route('/sync/parse-url', methods=['POST'])
    @validate_json(['urls'])
    def parse_url():
        """解析文档URL获取信息"""
        try:
            data = request.get_json()
            urls = data.get('urls', [])
            
            # 兼容单个URL的旧格式
            if 'url' in data and not urls:
                urls = [data.get('url')]
            
            document_service = DocumentService(logger=current_app.logger)
            result = document_service.parse_document_urls(urls)
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "VALIDATION_ERROR", status_code=400)
        except Exception as e:
            return APIResponse.error(f"URL解析失败: {str(e)}", "URL_PARSE_ERROR", status_code=500)

    @bp.route('/sync/manual', methods=['POST'])
    @validate_json(['document_ids', 'source_platform', 'target_platform'])
    def create_manual_sync():
        """创建手动同步任务"""
        try:
            data = request.get_json()
            document_ids = data.get('document_ids', [])
            source_platform = data.get('source_platform')
            target_platform = data.get('target_platform')
            force_resync = data.get('force_resync', False)
            notion_category = data.get('notion_category')
            notion_type = data.get('notion_type')
            
            document_service = DocumentService(logger=current_app.logger)
            result = document_service.create_manual_sync_tasks(
                document_ids, source_platform, target_platform, force_resync, notion_category, notion_type
            )
            return APIResponse.success(result)
            
        except ValueError as e:
            return APIResponse.error(str(e), "VALIDATION_ERROR", status_code=400)
        except Exception as e:
            return APIResponse.error(f"创建手动同步任务失败: {str(e)}", "MANUAL_SYNC_ERROR", status_code=500)

    @bp.route('/sync/history', methods=['GET'])
    @paginated(max_per_page=50)
    def get_sync_history():
        """获取同步历史记录"""
        try:
            limit = request.args.get('limit', 10, type=int)
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.get_sync_history(limit)
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取同步历史失败: {str(e)}", "SYNC_HISTORY_ERROR", status_code=500)

    @bp.route('/sync/batch', methods=['POST'])
    @validate_json(['document_ids'])
    def create_batch_sync():
        """创建批量同步任务"""
        try:
            data = request.get_json()
            document_ids = data.get('document_ids', [])
            force_sync = data.get('force_sync', False)
            
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.create_sync_records_batch(document_ids, force_sync)
            
            # 转换为旧版格式（向后兼容）
            created_records = [
                {
                    "record_number": record.get('record_number'),
                    "document_id": record.get('document_id'),
                    "status": "pending" if record.get('status') == 'created' else record.get('status')
                }
                for record in result.get('records', [])
                if record.get('status') == 'created'
            ]
            
            return APIResponse.success({
                "message": f"成功创建 {result.get('created_count', 0)} 个同步任务",
                "created_records": created_records
            })
            
        except ValueError as e:
            return APIResponse.error(str(e), "VALIDATION_ERROR", status_code=400)
        except Exception as e:
            return APIResponse.error(f"批量同步创建失败: {str(e)}", "BATCH_SYNC_ERROR", status_code=500)

    @bp.route('/batch/folder/scan', methods=['POST'])
    @validate_json(['folder_path'])
    def scan_folder():
        """扫描文件夹获取文档列表"""
        try:
            data = request.get_json()
            folder_path = data.get('folder_path', '')
            max_depth = data.get('max_depth', 2)
            use_cache = data.get('use_cache', True)
            
            document_service = DocumentService(logger=current_app.logger)
            
            # 提取文件夹ID
            folder_id = document_service.extract_folder_id_from_url(folder_path)
            
            # 扫描文件夹
            result = document_service.scan_feishu_folder(folder_id, max_depth, use_cache)
            return APIResponse.success(result)
            
        except ValueError as e:
            error_msg = str(e)
            if "认证失败" in error_msg:
                return APIResponse.error(error_msg, "AUTHENTICATION_FAILED", status_code=401)
            elif "无权限" in error_msg:
                return APIResponse.error(error_msg, "PERMISSION_DENIED", status_code=403)
            elif "不存在" in error_msg:
                return APIResponse.error(error_msg, "FOLDER_NOT_FOUND", status_code=404)
            elif "频率超限" in error_msg:
                return APIResponse.error(error_msg, "RATE_LIMIT", status_code=429)
            elif "未配置" in error_msg:
                return APIResponse.error(error_msg, "FEISHU_CONFIG_MISSING", status_code=503)
            else:
                return APIResponse.error(error_msg, "VALIDATION_ERROR", status_code=400)
        except Exception as e:
            return APIResponse.error(f"文件夹扫描失败: {str(e)}", "SCAN_ERROR", status_code=500)