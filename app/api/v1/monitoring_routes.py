#!/usr/bin/env python3
"""
监控相关API路由 - 处理系统监控和统计
"""
from flask import current_app
from app.utils import APIResponse
from app.services import SyncService, MonitoringService


def register_routes(bp):
    """注册监控相关路由到蓝图"""
    
    @bp.route('/dashboard', methods=['GET'])
    def get_dashboard_data():
        """获取仪表板数据"""
        try:
            sync_service = SyncService(logger=current_app.logger)
            result = sync_service.get_dashboard_stats()
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取仪表板数据失败: {str(e)}", "DASHBOARD_ERROR", status_code=500)

    @bp.route('/monitoring/performance', methods=['GET'])
    def get_performance_metrics():
        """获取性能监控指标"""
        try:
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.get_performance_trends()
            return APIResponse.success(result)
            
        except Exception as e:
            return APIResponse.error(f"获取性能指标失败: {str(e)}", "DATABASE_ERROR", status_code=500)

    @bp.route('/system/health', methods=['GET'])
    def health_check():
        """系统健康检查"""
        try:
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.get_system_health()
            return APIResponse.success(result)
            
        except Exception as e:
            return APIResponse.error(f"健康检查失败: {str(e)}", "HEALTH_CHECK_FAILED", status_code=503)

    @bp.route('/settings', methods=['GET'])
    def get_settings():
        """获取系统设置"""
        try:
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.get_system_settings()
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取系统设置失败: {str(e)}", "SETTINGS_ERROR", status_code=500)

    @bp.route('/logs/analysis', methods=['GET'])
    def get_logs_analysis():
        """获取日志分析数据"""
        try:
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.get_logs_analysis()
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取日志分析失败: {str(e)}", "LOGS_ANALYSIS_ERROR", status_code=500)

    @bp.route('/images/stats', methods=['GET'])
    def get_images_stats():
        """获取图片统计信息"""
        try:
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.get_images_stats()
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取图片统计失败: {str(e)}", "IMAGES_STATS_ERROR", status_code=500)

    @bp.route('/images/list', methods=['GET'])
    def get_images_list():
        """获取图片列表"""
        try:
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.get_images_list()
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取图片列表失败: {str(e)}", "IMAGES_LIST_ERROR", status_code=500)

    @bp.route('/images/<int:image_id>', methods=['DELETE'])
    def delete_image(image_id):
        """删除图片"""
        try:
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.delete_image(image_id)
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"删除图片失败: {str(e)}", "DELETE_IMAGE_ERROR", status_code=500)

    @bp.route('/sync/processor/status', methods=['GET'])
    def get_processor_status():
        """获取同步任务处理器状态"""
        try:
            from app.core.task_processor import get_task_processor
            
            monitoring_service = MonitoringService(logger=current_app.logger)
            sync_task_processor = get_task_processor()
            result = monitoring_service.get_processor_status(sync_task_processor)
            return APIResponse.success(result)
        except ValueError as e:
            return APIResponse.error(str(e), "PROCESSOR_NOT_INITIALIZED", status_code=500)
        except Exception as e:
            return APIResponse.error(f"获取处理器状态失败: {str(e)}", "PROCESSOR_STATUS_ERROR", status_code=500)

    @bp.route('/monitoring/realtime', methods=['GET'])
    def get_realtime_monitoring():
        """获取实时监控数据"""
        try:
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.get_realtime_data()
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取实时监控数据失败: {str(e)}", "REALTIME_MONITORING_ERROR", status_code=500)

    @bp.route('/monitoring/stats', methods=['GET'])
    def get_monitoring_stats():
        """获取监控统计数据"""
        try:
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.get_monitoring_stats()
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取监控统计失败: {str(e)}", "MONITORING_STATS_ERROR", status_code=500)

    @bp.route('/recent-activities', methods=['GET'])
    def get_recent_activities():
        """获取最近活动记录"""
        try:
            from flask import request
            limit = request.args.get('limit', 10, type=int)
            limit = min(limit, 50)  # 限制最大数量
            
            monitoring_service = MonitoringService(logger=current_app.logger)
            result = monitoring_service.get_recent_activities(limit)
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f"获取最近活动失败: {str(e)}", "RECENT_ACTIVITIES_ERROR", status_code=500)