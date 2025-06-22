#!/usr/bin/env python3
"""
Production Flask server for sync system
"""
import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template

# 创建图片存储目录
os.makedirs('/www/wwwroot/sync.yianlu.com/static/images', exist_ok=True)

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Helper functions
def generate_record_number():
    """Generate unique record number (auto-increment)"""
    conn = get_db_connection()
    try:
        # 获取当前最大ID
        result = conn.execute('SELECT MAX(id) FROM sync_records').fetchone()
        max_id = result[0] if result[0] is not None else 0
        next_id = max_id + 1
        return str(next_id)
    finally:
        conn.close()

def safe_row_to_dict(row, default_values=None):
    """Safely convert sqlite3.Row to dict with fallback handling"""
    if default_values is None:
        default_values = {}
    
    result = {}
    try:
        # Get column names from Row object
        keys = row.keys() if hasattr(row, 'keys') else []
        for key in keys:
            try:
                result[key] = row[key]
            except (KeyError, IndexError):
                result[key] = default_values.get(key, '')
    except Exception:
        # Fallback for problematic Row objects
        if hasattr(row, '__getitem__'):
            try:
                result = dict(row)
            except:
                pass
    
    # Apply default values for missing keys
    for key, default_val in default_values.items():
        if key not in result or result[key] is None:
            result[key] = default_val
            
    return result

# Database helper functions
def get_db_connection():
    """Get SQLite database connection with timeout and retry"""
    import time
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(
                '/www/wwwroot/sync.yianlu.com/feishu_notion_sync.db',
                timeout=10.0,  # 10 seconds timeout
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA busy_timeout=5000')  # 5 seconds busy timeout
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                raise e

def init_database():
    """Initialize database tables if they don't exist"""
    conn = get_db_connection()
    
    # Create sync_configs table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sync_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            document_id TEXT NOT NULL,
            is_sync_enabled BOOLEAN DEFAULT 1,
            sync_direction TEXT NOT NULL,
            auto_sync BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create sync_records table  
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sync_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_number TEXT UNIQUE,
            source_platform TEXT NOT NULL,
            target_platform TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT,
            content_type TEXT DEFAULT 'document',
            sync_status TEXT DEFAULT 'pending',
            error_message TEXT,
            last_sync_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create image_mappings table for image management
    conn.execute('''
        CREATE TABLE IF NOT EXISTS image_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_url TEXT NOT NULL,
            local_url TEXT,
            qiniu_url TEXT,
            file_hash TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_type TEXT DEFAULT 'image',
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            last_access_time TIMESTAMP,
            storage_type TEXT DEFAULT 'local'
        )
    ''')
    
    # Create performance indexes for frequently queried columns
    try:
        # Index for sync_records performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_records_status ON sync_records(sync_status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_records_created_at ON sync_records(created_at DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_records_updated_at ON sync_records(updated_at DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_records_source_platform ON sync_records(source_platform)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_records_composite ON sync_records(sync_status, created_at DESC)')
        
        # Index for sync_configs performance  
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_configs_platform ON sync_configs(platform)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_configs_document_id ON sync_configs(document_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_configs_enabled ON sync_configs(is_sync_enabled)')
        
        # Index for image_mappings performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_image_mappings_hash ON image_mappings(file_hash)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_image_mappings_storage_type ON image_mappings(storage_type)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_image_mappings_upload_time ON image_mappings(upload_time DESC)')
        
        print("✅ Database indexes created successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not create some indexes: {e}")
    
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/sync/configs')
def get_sync_configs():
    """Get all sync configurations"""
    try:
        conn = get_db_connection()
        configs = conn.execute('SELECT * FROM sync_configs ORDER BY created_at DESC').fetchall()
        conn.close()
        
        config_list = []
        for config in configs:
            config_list.append({
                'id': config['id'],
                'platform': config['platform'],
                'document_id': config['document_id'],
                'is_sync_enabled': bool(config['is_sync_enabled']),
                'sync_direction': config['sync_direction'],
                'auto_sync': bool(config['auto_sync']),
                'created_at': config['created_at'],
                'updated_at': config['updated_at']
            })
        
        return jsonify({
            "success": True,
            "data": config_list
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取配置失败: {str(e)}"
        }), 500

@app.route('/api/sync/config', methods=['POST'])
def save_sync_config():
    """Save or update sync configuration"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        
        # Check if config already exists
        existing = conn.execute(
            'SELECT id FROM sync_configs WHERE platform = ? AND document_id = ?',
            (data.get('platform'), data.get('document_id'))
        ).fetchone()
        
        if existing:
            # Update existing
            conn.execute('''
                UPDATE sync_configs 
                SET is_sync_enabled = ?, sync_direction = ?, auto_sync = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data.get('is_sync_enabled', True),
                data.get('sync_direction'),
                data.get('auto_sync', False),
                existing['id']
            ))
            config_id = existing['id']
        else:
            # Insert new
            cursor = conn.execute('''
                INSERT INTO sync_configs (platform, document_id, is_sync_enabled, sync_direction, auto_sync, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                data.get('platform'),
                data.get('document_id'),
                data.get('is_sync_enabled', True),
                data.get('sync_direction'),
                data.get('auto_sync', False)
            ))
            config_id = cursor.lastrowid
        
        conn.commit()
        
        # Get the saved config
        config = conn.execute('SELECT * FROM sync_configs WHERE id = ?', (config_id,)).fetchone()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "配置保存成功",
            "data": {
                'id': config['id'],
                'platform': config['platform'],
                'document_id': config['document_id'],
                'is_sync_enabled': bool(config['is_sync_enabled']),
                'sync_direction': config['sync_direction'],
                'auto_sync': bool(config['auto_sync']),
                'created_at': config['created_at'],
                'updated_at': config['updated_at']
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"保存配置失败: {str(e)}"
        }), 500

@app.route('/api/sync/config/<int:config_id>', methods=['GET'])
def get_sync_config(config_id):
    """Get single sync configuration"""
    try:
        conn = get_db_connection()
        config = conn.execute('SELECT * FROM sync_configs WHERE id = ?', (config_id,)).fetchone()
        conn.close()
        
        if config:
            return jsonify({
                "success": True,
                "data": {
                    'id': config['id'],
                    'platform': config['platform'],
                    'document_id': config['document_id'],
                    'is_sync_enabled': bool(config['is_sync_enabled']),
                    'sync_direction': config['sync_direction'],
                    'auto_sync': bool(config['auto_sync']),
                    'created_at': config['created_at'],
                    'updated_at': config['updated_at']
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "配置不存在"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取配置失败: {str(e)}"
        }), 500

@app.route('/api/sync/config/<int:config_id>', methods=['PUT'])
def update_sync_config(config_id):
    """Update sync configuration"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        
        # Update config
        conn.execute('''
            UPDATE sync_configs 
            SET platform = ?, document_id = ?, is_sync_enabled = ?, 
                sync_direction = ?, auto_sync = ?, updated_at = ?
            WHERE id = ?
        ''', (
            data.get('platform'),
            data.get('document_id'),
            data.get('is_sync_enabled', True),
            data.get('sync_direction'),
            data.get('auto_sync', False),
            datetime.utcnow().isoformat(),
            config_id
        ))
        
        conn.commit()
        
        # Get updated config
        config = conn.execute('SELECT * FROM sync_configs WHERE id = ?', (config_id,)).fetchone()
        conn.close()
        
        if config:
            return jsonify({
                "success": True,
                "message": "配置更新成功",
                "data": {
                    'id': config['id'],
                    'platform': config['platform'],
                    'document_id': config['document_id'],
                    'is_sync_enabled': bool(config['is_sync_enabled']),
                    'sync_direction': config['sync_direction'],
                    'auto_sync': bool(config['auto_sync']),
                    'created_at': config['created_at'],
                    'updated_at': config['updated_at']
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "配置不存在"
            }), 404
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新配置失败: {str(e)}"
        }), 500

@app.route('/api/sync/config/<int:config_id>', methods=['DELETE'])
def delete_sync_config(config_id):
    """Delete sync configuration"""
    try:
        conn = get_db_connection()
        
        # Check if config exists
        config = conn.execute('SELECT * FROM sync_configs WHERE id = ?', (config_id,)).fetchone()
        if not config:
            conn.close()
            return jsonify({
                "success": False,
                "message": "配置不存在"
            }), 404
        
        # Delete the config
        conn.execute('DELETE FROM sync_configs WHERE id = ?', (config_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "配置删除成功"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"删除配置失败: {str(e)}"
        }), 500

@app.route('/api/sync/trigger', methods=['POST'])
def trigger_sync():
    """Trigger sync operation with real API integration"""
    sync_record_id = None
    conn = None
    
    try:
        data = request.get_json()
        source_platform = data.get('source_platform')
        target_platform = data.get('target_platform')
        source_id = data.get('source_id')
        content_type = data.get('content_type', 'document')
        
        # Create initial sync record
        conn = get_db_connection()
        record_number = generate_record_number()
        cursor = conn.execute('''
            INSERT INTO sync_records (record_number, source_platform, target_platform, source_id, content_type, sync_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record_number,
            source_platform,
            target_platform,
            source_id,
            content_type,
            'processing',
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        sync_record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        conn = None
        
        # Import and use real sync services
        from sync_services import SyncProcessor
        processor = SyncProcessor()
        
        # Perform actual sync
        if source_platform == 'feishu' and target_platform == 'notion':
            sync_result = processor.sync_feishu_to_notion(source_id)
        else:
            sync_result = {
                'success': False,
                'error': f'不支持的同步方向: {source_platform} -> {target_platform}'
            }
        
        # Update sync record with results
        conn = get_db_connection()
        if sync_result['success']:
            conn.execute('''
                UPDATE sync_records 
                SET sync_status = ?, target_id = ?, last_sync_time = ?, updated_at = ?
                WHERE id = ?
            ''', (
                'success', 
                sync_result.get('target_id', ''),
                datetime.utcnow().isoformat(), 
                datetime.utcnow().isoformat(), 
                sync_record_id
            ))
            conn.commit()
            conn.close()
            
            return jsonify({
                "success": True,
                "message": "同步成功！已在Notion中创建新的Post记录",
                "sync_record_id": sync_record_id,
                "result": sync_result
            })
        else:
            conn.execute('''
                UPDATE sync_records 
                SET sync_status = ?, error_message = ?, updated_at = ?
                WHERE id = ?
            ''', (
                'failed', 
                sync_result.get('error', '未知错误'),
                datetime.utcnow().isoformat(), 
                sync_record_id
            ))
            conn.commit()
            conn.close()
            
            return jsonify({
                "success": False,
                "message": f"同步失败: {sync_result.get('error')}",
                "sync_record_id": sync_record_id,
                "result": sync_result
            }), 500
        
    except Exception as e:
        # Ensure database connection is closed
        if conn:
            try:
                conn.close()
            except:
                pass
        
        # Update sync record with error if we have a record ID
        if sync_record_id:
            try:
                error_conn = get_db_connection()
                error_conn.execute('''
                    UPDATE sync_records 
                    SET sync_status = ?, error_message = ?, updated_at = ?
                    WHERE id = ?
                ''', ('failed', f'系统异常: {str(e)}', datetime.utcnow().isoformat(), sync_record_id))
                error_conn.commit()
                error_conn.close()
            except Exception as db_error:
                print(f"Failed to update error status in database: {db_error}")
                
        print(f"Sync trigger error: {e}")
        return jsonify({
            "success": False,
            "message": f"系统异常: {str(e)}",
            "sync_record_id": sync_record_id
        }), 500

@app.route('/api/sync/records')
def get_sync_records():
    """Get sync records with pagination and optimized sqlite3.Row handling"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)  # Cap at 100
        status_filter = request.args.get('status', '')
        
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        
        # Build query with optional status filter
        where_clause = ""
        params = []
        if status_filter:
            where_clause = "WHERE sync_status = ?"
            params.append(status_filter)
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) as total FROM sync_records {where_clause}"
        total_records = conn.execute(count_query, params).fetchone()['total']
        
        # Get paginated records
        query = f'''
            SELECT id, record_number, source_platform, target_platform, source_id, 
                   target_id, content_type, sync_status, error_message, 
                   last_sync_time, created_at, updated_at
            FROM sync_records 
            {where_clause}
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        '''
        params.extend([limit, offset])
        
        records = conn.execute(query, params).fetchall()
        conn.close()
        
        record_list = []
        for record in records:
            # Safe sqlite3.Row attribute access using getattr with fallback
            try:
                record_number = record['record_number'] if record['record_number'] else str(record['id'])
            except (KeyError, AttributeError):
                record_number = str(record['id'])
                
            record_list.append({
                'id': record['id'],
                'record_number': record_number,
                'source_platform': record['source_platform'],
                'target_platform': record['target_platform'],
                'source_id': record['source_id'],
                'target_id': record['target_id'] or '',
                'content_type': record['content_type'] or 'document',
                'sync_status': record['sync_status'],
                'error_message': record['error_message'] or '',
                'last_sync_time': record['last_sync_time'] or '',
                'created_at': record['created_at'],
                'updated_at': record['updated_at']
            })
        
        return jsonify({
            "success": True,
            "data": {
                "records": record_list,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_records,
                    "pages": (total_records + limit - 1) // limit
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取同步记录失败: {str(e)}"
        }), 500

@app.route('/api/dashboard')
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db_connection()
        
        # Get config counts
        total_configs = conn.execute('SELECT COUNT(*) as count FROM sync_configs').fetchone()['count']
        enabled_configs = conn.execute('SELECT COUNT(*) as count FROM sync_configs WHERE is_sync_enabled = 1').fetchone()['count']
        
        # Get sync record counts
        total_syncs = conn.execute('SELECT COUNT(*) as count FROM sync_records').fetchone()['count']
        success_syncs = conn.execute('SELECT COUNT(*) as count FROM sync_records WHERE sync_status = "success"').fetchone()['count']
        failed_syncs = conn.execute('SELECT COUNT(*) as count FROM sync_records WHERE sync_status = "failed"').fetchone()['count']
        pending_syncs = conn.execute('SELECT COUNT(*) as count FROM sync_records WHERE sync_status = "pending"').fetchone()['count']
        
        conn.close()
        
        return jsonify({
            "success": True,
            "summary": {
                "total_syncs": total_syncs,
                "success_rate": round((success_syncs / total_syncs * 100) if total_syncs > 0 else 0, 1),
                "pending_tasks": pending_syncs,
                "enabled_configs": enabled_configs
            },
            "system_status": {
                "database": "connected",
                "feishu_api": "configured", 
                "notion_api": "configured",
                "qiniu_storage": "configured"
            },
            "data": {
                "configs": {
                    "total": total_configs,
                    "enabled": enabled_configs
                },
                "syncs": {
                    "total": total_syncs,
                    "success": success_syncs,
                    "failed": failed_syncs,
                    "pending": pending_syncs
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取统计数据失败: {str(e)}"
        }), 500

@app.route('/api/sync/history')
def get_sync_history():
    """Get sync history for dashboard with optimized performance"""
    try:
        # Get recent sync history with better performance
        limit = min(int(request.args.get('limit', 10)), 50)  # Dashboard optimized limit
        
        conn = get_db_connection()
        
        # Optimized query with specific columns only
        records = conn.execute('''
            SELECT id, record_number, source_platform, target_platform, source_id,
                   sync_status, last_sync_time, created_at, error_message
            FROM sync_records 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,)).fetchall()
        
        # Get summary stats efficiently
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN sync_status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN sync_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                SUM(CASE WHEN sync_status = 'pending' THEN 1 ELSE 0 END) as pending_count
            FROM sync_records
        ''').fetchone()
        
        conn.close()
        
        history_list = []
        for record in records:
            # Safe sqlite3.Row access
            try:
                record_number = record['record_number'] if record['record_number'] else str(record['id'])
            except (KeyError, AttributeError):
                record_number = str(record['id'])
                
            history_list.append({
                'id': record['id'],
                'record_number': record_number,
                'source_platform': record['source_platform'],
                'target_platform': record['target_platform'], 
                'source_id': record['source_id'],
                'sync_status': record['sync_status'],
                'last_sync_time': record['last_sync_time'] or '',
                'created_at': record['created_at'],
                'error_message': record['error_message'] or '' if record['sync_status'] == 'failed' else ''
            })
        
        return jsonify({
            "success": True,
            "data": {
                "history": history_list,
                "summary": {
                    "total": stats['total'],
                    "success_count": stats['success_count'],
                    "failed_count": stats['failed_count'],
                    "pending_count": stats['pending_count'],
                    "success_rate": round((stats['success_count'] / stats['total'] * 100) if stats['total'] > 0 else 0, 1)
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取同步历史失败: {str(e)}"
        }), 500

@app.route('/api/sync/pending')
def get_pending_syncs():
    """Get pending sync records with pagination and optimized handling"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        
        # Get total count
        total_pending = conn.execute('SELECT COUNT(*) as total FROM sync_records WHERE sync_status = "pending"').fetchone()['total']
        
        # Get paginated pending records (oldest first for processing priority)
        records = conn.execute('''
            SELECT id, record_number, source_platform, target_platform, source_id,
                   target_id, content_type, sync_status, created_at, updated_at
            FROM sync_records 
            WHERE sync_status = "pending"
            ORDER BY created_at ASC 
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        conn.close()
        
        record_list = []
        for record in records:
            # Safe sqlite3.Row attribute access
            try:
                record_number = record['record_number'] if record['record_number'] else str(record['id'])
            except (KeyError, AttributeError):
                record_number = str(record['id'])
                
            record_list.append({
                'id': record['id'],
                'record_number': record_number,
                'source_platform': record['source_platform'],
                'target_platform': record['target_platform'],
                'source_id': record['source_id'],
                'target_id': record['target_id'] or '',
                'content_type': record['content_type'] or 'document',
                'sync_status': record['sync_status'],
                'created_at': record['created_at'],
                'updated_at': record['updated_at']
            })
        
        return jsonify({
            "success": True,
            "data": {
                "records": record_list,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_pending,
                    "pages": (total_pending + limit - 1) // limit
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取待处理同步记录失败: {str(e)}"
        }), 500

@app.route('/api/sync/failed')
def get_failed_syncs():
    """Get failed sync records with pagination and optimized sqlite3.Row handling"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        
        # Get total count
        total_failed = conn.execute('SELECT COUNT(*) as total FROM sync_records WHERE sync_status = "failed"').fetchone()['total']
        
        # Get paginated failed records
        records = conn.execute('''
            SELECT id, record_number, source_platform, target_platform, source_id,
                   target_id, content_type, sync_status, error_message,
                   last_sync_time, created_at, updated_at
            FROM sync_records 
            WHERE sync_status = "failed"
            ORDER BY updated_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        conn.close()
        
        record_list = []
        for record in records:
            # Safe sqlite3.Row attribute access
            try:
                record_number = record['record_number'] if record['record_number'] else str(record['id'])
            except (KeyError, AttributeError):
                record_number = str(record['id'])
                
            record_list.append({
                'id': record['id'],
                'record_number': record_number,
                'source_platform': record['source_platform'],
                'target_platform': record['target_platform'],
                'source_id': record['source_id'],
                'target_id': record['target_id'] or '',
                'content_type': record['content_type'] or 'document',
                'sync_status': record['sync_status'],
                'error_message': record['error_message'] or '',
                'last_sync_time': record['last_sync_time'] or '',
                'created_at': record['created_at'],
                'updated_at': record['updated_at']
            })
        
        return jsonify({
            "success": True,
            "data": {
                "records": record_list,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_failed,
                    "pages": (total_failed + limit - 1) // limit
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取失败同步记录失败: {str(e)}"
        }), 500

@app.route('/api/sync/record/<int:record_id>', methods=['DELETE'])
def delete_sync_record(record_id):
    """Delete a single sync record"""
    try:
        conn = get_db_connection()
        
        # Check if record exists
        record = conn.execute('SELECT * FROM sync_records WHERE id = ?', (record_id,)).fetchone()
        if not record:
            conn.close()
            return jsonify({
                "success": False,
                "message": "同步记录不存在"
            }), 404
        
        # Delete the record
        conn.execute('DELETE FROM sync_records WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "记录删除成功"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"删除记录失败: {str(e)}"
        }), 500

@app.route('/api/sync/records/clear', methods=['DELETE'])
def clear_sync_records():
    """Clear sync records by status or all records"""
    try:
        status = request.args.get('status')  # success, failed, pending, all
        
        conn = get_db_connection()
        
        if status and status != 'all':
            # Delete records with specific status
            deleted = conn.execute('DELETE FROM sync_records WHERE sync_status = ?', (status,))
            message = f"已删除所有{status}状态的记录"
        else:
            # Delete all records
            deleted = conn.execute('DELETE FROM sync_records')
            message = "已删除所有同步记录"
        
        conn.commit()
        rows_affected = deleted.rowcount
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"{message}，共删除{rows_affected}条记录"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"清空记录失败: {str(e)}"
        }), 500

@app.route('/api/sync/records/batch', methods=['DELETE'])
def delete_sync_records_batch():
    """Delete multiple sync records by IDs"""
    try:
        data = request.get_json()
        record_ids = data.get('record_ids', [])
        
        if not record_ids:
            return jsonify({
                "success": False,
                "message": "未提供要删除的记录ID"
            }), 400
        
        conn = get_db_connection()
        
        # Create placeholders for the IN clause
        placeholders = ','.join('?' * len(record_ids))
        query = f'DELETE FROM sync_records WHERE id IN ({placeholders})'
        
        deleted = conn.execute(query, record_ids)
        conn.commit()
        rows_affected = deleted.rowcount
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"成功删除{rows_affected}条记录"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"批量删除失败: {str(e)}"
        }), 500

@app.route('/api/sync/config/<int:config_id>/toggle', methods=['POST'])
def toggle_sync_config(config_id):
    """Toggle sync configuration enable/disable status"""
    try:
        conn = get_db_connection()
        
        # Get current config
        config = conn.execute('SELECT * FROM sync_configs WHERE id = ?', (config_id,)).fetchone()
        if not config:
            conn.close()
            return jsonify({
                "success": False,
                "message": "配置不存在"
            }), 404
        
        # Toggle the enable status
        new_status = not bool(config['is_sync_enabled'])
        
        # Update config
        conn.execute('''
            UPDATE sync_configs 
            SET is_sync_enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_status, config_id))
        
        conn.commit()
        
        # Get updated config
        updated_config = conn.execute('SELECT * FROM sync_configs WHERE id = ?', (config_id,)).fetchone()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"配置已{'启用' if new_status else '禁用'}",
            "data": {
                'id': updated_config['id'],
                'platform': updated_config['platform'],
                'document_id': updated_config['document_id'],
                'is_sync_enabled': bool(updated_config['is_sync_enabled']),
                'sync_direction': updated_config['sync_direction'],
                'auto_sync': bool(updated_config['auto_sync']),
                'created_at': updated_config['created_at'],
                'updated_at': updated_config['updated_at']
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"切换配置状态失败: {str(e)}"
        }), 500

@app.route('/api/sync/retry/<int:record_id>', methods=['POST'])
def retry_sync(record_id):
    """Retry a failed sync operation"""
    try:
        conn = get_db_connection()
        
        # Get the sync record
        record = conn.execute('SELECT * FROM sync_records WHERE id = ?', (record_id,)).fetchone()
        if not record:
            conn.close()
            return jsonify({
                "success": False,
                "message": "同步记录不存在"
            }), 404
        
        # Update record status to processing
        conn.execute('''
            UPDATE sync_records 
            SET sync_status = ?, error_message = NULL, updated_at = ?
            WHERE id = ?
        ''', ('processing', datetime.utcnow().isoformat(), record_id))
        
        # Real retry processing with actual API calls
        from sync_services import SyncProcessor
        processor = SyncProcessor()
        
        # Perform actual sync retry
        if record['source_platform'] == 'feishu' and record['target_platform'] == 'notion':
            sync_result = processor.sync_feishu_to_notion(record['source_id'])
        else:
            sync_result = {
                'success': False,
                'error': f'不支持的同步方向: {record["source_platform"]} -> {record["target_platform"]}'
            }
        
        if sync_result['success']:
            # Update with success
            conn.execute('''
                UPDATE sync_records 
                SET sync_status = ?, target_id = ?, error_message = NULL, last_sync_time = ?, updated_at = ?
                WHERE id = ?
            ''', (
                'success', 
                sync_result.get('target_id', ''),
                datetime.utcnow().isoformat(), 
                datetime.utcnow().isoformat(), 
                record_id
            ))
            
            result = {
                "success": True,
                "action": "retry",
                "target_id": sync_result.get('target_id'),
                "target_url": sync_result.get('target_url'),
                "title": sync_result.get('title', f"重试文档 - {record['source_id']}"),
                "retry_count": 1
            }
        else:
            # Update with failure
            conn.execute('''
                UPDATE sync_records 
                SET sync_status = ?, error_message = ?, updated_at = ?
                WHERE id = ?
            ''', ('failed', sync_result.get('error', '重试失败'), datetime.utcnow().isoformat(), record_id))
            
            result = {
                "success": False,
                "error": sync_result.get('error', '重试失败')
            }
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "重试完成",
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"重试失败: {str(e)}"
        }), 500

@app.route('/api/images/stats')
def get_image_stats():
    """Get image storage statistics"""
    try:
        conn = get_db_connection()
        
        # 图片统计
        total_images = conn.execute('SELECT COUNT(*) as count FROM image_mappings').fetchone()['count']
        total_size = conn.execute('SELECT SUM(file_size) as size FROM image_mappings').fetchone()['size'] or 0
        total_access = conn.execute('SELECT SUM(access_count) as access FROM image_mappings').fetchone()['access'] or 0
        
        # 按存储类型统计
        local_count = conn.execute('SELECT COUNT(*) as count FROM image_mappings WHERE storage_type = "local"').fetchone()['count']
        qiniu_count = conn.execute('SELECT COUNT(*) as count FROM image_mappings WHERE storage_type = "qiniu"').fetchone()['count']
        
        # 最近上传的图片
        recent_images = conn.execute('''
            SELECT * FROM image_mappings 
            ORDER BY upload_time DESC 
            LIMIT 10
        ''').fetchall()
        
        conn.close()
        
        # 计算平均大小
        avg_size = round(total_size / total_images, 2) if total_images > 0 else 0
        
        # 本地存储目录大小
        import os
        local_storage_path = '/www/wwwroot/sync.yianlu.com/static/images'
        local_storage_size = 0
        try:
            for root, dirs, files in os.walk(local_storage_path):
                for file in files:
                    local_storage_size += os.path.getsize(os.path.join(root, file))
        except:
            pass
        
        recent_list = []
        for img in recent_images:
            recent_list.append({
                'id': img['id'],
                'file_hash': img['file_hash'],
                'file_size': img['file_size'],
                'file_type': img['file_type'],
                'storage_type': img['storage_type'],
                'access_count': img['access_count'],
                'upload_time': img['upload_time']
            })
        
        return jsonify({
            "success": True,
            "data": {
                "summary": {
                    "total_images": total_images,
                    "total_size_mb": round(total_size / 1024 / 1024, 2),
                    "total_access_count": total_access,
                    "average_size_kb": round(avg_size / 1024, 2),
                    "local_storage_mb": round(local_storage_size / 1024 / 1024, 2)
                },
                "storage_distribution": {
                    "local_count": local_count,
                    "qiniu_count": qiniu_count
                },
                "recent_images": recent_list
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取图片统计失败: {str(e)}"
        }), 500

@app.route('/api/images')
def get_images():
    """Get image list with pagination"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        storage_type = request.args.get('storage_type', '')
        
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        
        # 构建查询条件
        where_clause = ""
        params = []
        if storage_type:
            where_clause = "WHERE storage_type = ?"
            params.append(storage_type)
        
        # 获取图片列表
        query = f'''
            SELECT * FROM image_mappings 
            {where_clause}
            ORDER BY upload_time DESC 
            LIMIT ? OFFSET ?
        '''
        params.extend([limit, offset])
        
        images = conn.execute(query, params).fetchall()
        
        # 获取总数
        count_query = f"SELECT COUNT(*) as count FROM image_mappings {where_clause}"
        total = conn.execute(count_query, params[:-2] if where_clause else []).fetchone()['count']
        
        conn.close()
        
        image_list = []
        for img in images:
            image_list.append({
                'id': img['id'],
                'original_url': img['original_url'],
                'local_url': img['local_url'],
                'qiniu_url': img['qiniu_url'],
                'file_hash': img['file_hash'],
                'file_size': img['file_size'],
                'file_size_kb': round(img['file_size'] / 1024, 2),
                'file_type': img['file_type'],
                'storage_type': img['storage_type'],
                'access_count': img['access_count'],
                'upload_time': img['upload_time'],
                'last_access_time': img['last_access_time']
            })
        
        return jsonify({
            "success": True,
            "data": {
                "images": image_list,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取图片列表失败: {str(e)}"
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    print("🚀 启动飞书-Notion同步服务...")
    print("📍 服务地址: http://0.0.0.0:5000")
    print("🌐 Webhook地址: https://sync.yianlu.com/webhook/feishu")
    print("🔍 健康检查: https://sync.yianlu.com/health")
    print("📊 管理面板: https://sync.yianlu.com/")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False
    )