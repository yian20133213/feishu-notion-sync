#!/usr/bin/env python3
"""
修复images表结构的迁移脚本
"""
import sqlite3
import os

def fix_images_table():
    """修复images表结构"""
    db_path = 'feishu_notion_sync.db'
    
    if not os.path.exists(db_path):
        print(f"数据库文件 {db_path} 不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 首先检查当前表结构
        cursor.execute('PRAGMA table_info(images)')
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print("当前images表结构:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # 检查缺少的列
        missing_columns = []
        
        if 'qiniu_url' not in column_names:
            missing_columns.append('qiniu_url')
            
        if 'file_hash' not in column_names and 'hash' in column_names:
            # 需要重命名hash列为file_hash
            print("\n需要重命名 hash 列为 file_hash")
            
        if missing_columns:
            print(f"\n缺少列: {missing_columns}")
            
            # 添加缺少的列
            for col in missing_columns:
                if col == 'qiniu_url':
                    cursor.execute('ALTER TABLE images ADD COLUMN qiniu_url VARCHAR(500)')
                    print(f"已添加列: {col}")
        
        # 如果需要重命名hash为file_hash，需要重建表
        if 'hash' in column_names and 'file_hash' not in column_names:
            print("\n开始重建表以重命名列...")
            
            # 创建临时表
            cursor.execute('''
                CREATE TABLE images_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename VARCHAR(255) NOT NULL,
                    original_url VARCHAR(500),
                    qiniu_url VARCHAR(500),
                    local_path VARCHAR(500),
                    size INTEGER,
                    mime_type VARCHAR(100),
                    file_hash VARCHAR(64),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    sync_record_id INTEGER
                )
            ''')
            
            # 复制数据
            cursor.execute('''
                INSERT INTO images_new (id, filename, original_url, qiniu_url, local_path, size, mime_type, file_hash, created_at, sync_record_id)
                SELECT id, filename, original_url, NULL, local_path, size, mime_type, hash, created_at, sync_record_id
                FROM images
            ''')
            
            # 删除旧表
            cursor.execute('DROP TABLE images')
            
            # 重命名新表
            cursor.execute('ALTER TABLE images_new RENAME TO images')
            
            print("表重建完成")
        
        # 创建索引
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_sync_record ON images (sync_record_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_original_url ON images (original_url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON images (file_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON images (created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_filename ON images (filename)')
            print("索引创建完成")
        except Exception as e:
            print(f"创建索引时出错: {e}")
        
        conn.commit()
        
        # 验证修复结果
        cursor.execute('PRAGMA table_info(images)')
        new_columns = cursor.fetchall()
        
        print("\n修复后的images表结构:")
        for col in new_columns:
            print(f"  {col[1]} ({col[2]})")
        
        conn.close()
        print("\n✅ 数据库修复完成")
        
    except Exception as e:
        print(f"❌ 修复过程中出错: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    fix_images_table()