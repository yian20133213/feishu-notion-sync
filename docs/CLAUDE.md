# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Feishu-Notion bidirectional synchronization system that enables automatic content syncing between Feishu (Lark) documents and Notion pages. The system includes image processing, format conversion, and a web management interface.

## Recent Critical Updates (2025-06-30)

### ✅ Fixed Critical Issues
1. **Hardcoded Paths Fixed**: Replaced all hardcoded `/www/wwwroot/sync.yianlu.com/` paths with dynamic `PROJECT_ROOT` variables
2. **Database Layer Unified**: Migrated from conflicting raw SQLite + SQLAlchemy to pure SQLAlchemy ORM
3. **Dependencies Cleaned**: Removed redundant packages (fastapi, pymysql, requests, aiohttp) from requirements.txt
4. **HTTP Client Standardized**: All HTTP requests now use `httpx` instead of mixed `requests`/`aiohttp`
5. **Database Migrations**: Added Alembic support for proper schema management

### ⚠️ Breaking Changes
- **Database Code**: Old `app/core/database.py` raw SQLite implementation is deprecated
- **HTTP Libraries**: All code now uses `httpx` instead of `requests`
- **Paths**: All file paths are now relative to project root, not hardcoded

## Commands

### Database Migration (IMPORTANT - Run First)
```bash
# Migrate from old SQLite to new SQLAlchemy
cd /www/wwwroot/sync.yianlu.com
python database/migration_service.py

# Initialize Alembic migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Running the Development Server
```bash
cd /www/wwwroot/sync.yianlu.com
python app.py
```
The Flask application runs on port 5000 with Nginx reverse proxy configured.

**Note**: `production_server.py` is deprecated - always use `app.py`

### Health Check
```bash
curl https://sync.yianlu.com/health
curl http://localhost:5000/health  # local development
```

### Service Management
```bash
# Check if service is running
ps aux | grep python
sudo systemctl status sync-service  # if systemd service is configured

# Start service in background
nohup python app.py > server.log 2>&1 &

# Kill existing service
pkill -f "python app.py"
```

### Development & Debugging
```bash
# Install dependencies
pip install -r requirements.txt

# Check logs
tail -f app.log
tail -f service.log

# Debug mode (only for development)
FLASK_ENV=development python app.py

# View database records (using SQLAlchemy now)
python -c "
from database.connection import db
from database.models import SyncRecord, SyncConfig, ImageMapping
with db.get_session() as session:
    records = session.query(SyncRecord).order_by(SyncRecord.created_at.desc()).limit(10).all()
    for r in records: print(f'{r.id}: {r.source_platform}->{r.target_platform} ({r.sync_status})')
"
```

## Architecture

### Core Components
- **Flask Application Factory**: Main application entry point (`app.py`) using application factory pattern
- **Core Module**: Application factory and configuration (`app/core/`)
  - `app_factory.py`: Flask application factory with blueprint registration (✅ Updated with dynamic paths)
  - ~~`database.py`: Raw SQLite implementation~~ (❌ DEPRECATED)
  - `task_processor.py`: Background sync task processing
- **Database Layer**: **NEW** Unified SQLAlchemy implementation
  - `database/connection.py`: SQLAlchemy engine and session management
  - `database/models.py`: SQLAlchemy ORM models (SyncRecord, SyncConfig, ImageMapping)
  - `database/migration_service.py`: Migration from old to new database layer
  - `alembic/`: Database migration scripts and configuration
- **API Layer**: RESTful endpoints in `app/api/`
  - `v1/`: Versioned API endpoints
    - `sync_routes.py`: Sync configuration and operations
    - `monitoring_routes.py`: System monitoring and stats
    - `config_routes.py`: Configuration management
  - `webhook.py`: Webhook handlers for Feishu events (legacy)
- **Web Layer**: Web interface blueprints (`app/web/`)
  - `main.py`: Main web interface blueprint
  - `admin.py`: Admin interface blueprint
- **Service Layer**: Business logic in `app/services/`
  - `feishu_client.py`: Feishu API integration (✅ Updated to use httpx)
  - `notion_client.py`: Notion API integration (✅ Updated to use httpx)
  - `qiniu_client.py`: Image storage and CDN (✅ Updated to use httpx)
  - `sync_processor.py`: Core sync processing logic
  - `sync_service.py`: High-level sync orchestration (✅ Updated with dynamic paths)
  - `document_service.py`: Document handling service
  - `monitoring_service.py`: System monitoring service
- **Configuration**: Environment-based settings (`config/`)
  - `settings.py`: Application settings (✅ Updated with dynamic paths)
- **Utilities**: Common utilities and helpers (`app/utils/`)
  - `decorators.py`: Common decorators for API endpoints
  - `helpers.py`: Utility functions
  - `schemas.py`: Data validation schemas

### Technology Stack
- **Backend**: Python 3.6+ + Flask
- **Database**: SQLite with SQLAlchemy ORM (✅ Migrated from raw SQLite)
- **HTTP Client**: httpx (✅ Unified from requests/aiohttp)
- **Image Storage**: Qiniu Cloud CDN
- **Frontend**: Vanilla JavaScript with HTML templates
- **Deployment**: Linux + Nginx + Baota Panel
- **External APIs**: Feishu API, Notion API
- **Database Migrations**: Alembic (✅ Newly added)

### Key Architecture Patterns
- **Application Factory Pattern**: Flask app creation through factory function in `app/core/app_factory.py`
- **Blueprint-Based Routing**: Modular routing with versioned API (`/api/v1/`) and web blueprints
- **Service-Oriented Architecture**: Clear separation between API, services, and data layers
- **Database-First Design**: SQLAlchemy models define the data structure
- **Configuration Management**: Environment-based configuration via `config/settings.py`
- **Background Task Processing**: Dedicated task processor for sync operations with threading
- **RESTful API Design**: Standardized endpoints for CRUD operations with proper versioning

### Important Development Notes
- **Database Access**: Use SQLAlchemy ORM with `database.connection.db.get_session()` context manager
- **HTTP Requests**: Always use `httpx.Client()` for HTTP requests
- **File Paths**: All paths use dynamic `PROJECT_ROOT` variable, never hardcoded paths
- **Deprecated Routes**: The `/dashboard` route is deprecated - all new functionality should go in the main `/` route
- **Legacy Code**: `production_server.py` and `app/core/database.py` are deprecated
- **API Versioning**: All new API endpoints should be added to `/api/v1/` namespace

## Configuration

### Environment Variables
Create a `.env` file in the project root:
```bash
# Feishu API Configuration
FEISHU_APP_ID="your_app_id"
FEISHU_APP_SECRET="your_app_secret"

# Notion API Configuration
NOTION_TOKEN="your_notion_token"
NOTION_TEST_PAGE_ID="your_test_page_id"

# Qiniu Cloud Configuration
QINIU_ACCESS_KEY="your_access_key"
QINIU_SECRET_KEY="your_secret_key"
QINIU_BUCKET="your_bucket_name"
QINIU_CDN_DOMAIN="https://your-cdn-domain.com"

# Database Configuration (now uses dynamic paths)
DATABASE_URL="sqlite:///./feishu_notion_sync.db"  # or MySQL URL

# Server Configuration
DEBUG=False
HOST=0.0.0.0
PORT=5000
SECRET_KEY="your_secret_key"

# Redis Configuration (optional)
REDIS_URL="redis://localhost:6379/0"
```

### Service URLs
- **Main Service**: https://sync.yianlu.com
- **Webhook URL**: https://sync.yianlu.com/webhook/feishu
- **Health Check**: https://sync.yianlu.com/health
- **Dashboard**: https://sync.yianlu.com/
- **CDN Domain**: https://cdn.yianlu.com

## Database Schema (NEW SQLAlchemy Models)

### SyncRecord
- `id`: Primary key
- `record_number`: Unique record identifier
- `source_platform`: 'feishu' or 'notion'
- `target_platform`: 'notion' or 'feishu'
- `source_id`: Source document ID
- `target_id`: Target document ID
- `content_type`: 'document', 'database', 'page'
- `sync_status`: 'pending', 'processing', 'success', 'failed'
- `last_sync_time`: Timestamp of last sync
- `error_message`: Error details if failed
- `created_at`, `updated_at`: Timestamps

### SyncConfig
- `id`: Primary key
- `platform`: 'feishu' or 'notion'
- `document_id`: Document identifier
- `sync_direction`: 'bidirectional', 'feishu_to_notion'
- `is_sync_enabled`: Boolean flag
- `auto_sync`: Auto sync enabled
- `webhook_url`: Webhook endpoint
- `created_at`, `updated_at`: Timestamps

### ImageMapping (previously images)
- `id`: Primary key
- `filename`: Image filename
- `original_url`: Original image URL
- `local_path`: Local file path
- `size`: File size in bytes
- `mime_type`: MIME type
- `hash`: MD5 hash for deduplication
- `sync_record_id`: Foreign key to SyncRecord
- `created_at`: Upload timestamp

## Development Notes

### Migration Guide
If you're working with existing code, follow this migration path:

1. **Database Code**: Replace all imports from `app.core.database` with `database.connection` and `database.models`
2. **HTTP Requests**: Replace `requests` imports with `httpx`
3. **File Paths**: Replace hardcoded paths with `PROJECT_ROOT` based paths
4. **Run Migration**: Execute `python database/migration_service.py` to migrate data

### Current Implementation Status
- ✅ Flask web server with modular architecture
- ✅ SQLAlchemy ORM with proper models and migrations
- ✅ Unified httpx HTTP client across all services
- ✅ Dynamic file path handling
- ✅ Feishu webhook handling and API integration
- ✅ Notion API client implementation
- ✅ Image processing and Qiniu Cloud storage
- ✅ Web dashboard for sync management
- ✅ Comprehensive error handling and logging
- ✅ RESTful API endpoints for all operations

### Sync Strategy
- **Feishu → Notion**: Real-time automatic sync (webhook-triggered)
- **Notion → Feishu**: Manual confirmation sync (web interface)
- **Content Format**: Unified Markdown as intermediate format
- **Image Processing**: Auto-upload to Qiniu Cloud with WebP compression
- **Deduplication**: MD5-based image deduplication

### Error Handling
- Comprehensive logging with rotating file handlers
- Database transaction rollback on errors
- Retry mechanisms for failed sync operations
- Graceful webhook signature verification
- Thread-safe operations with proper locking

### Security Considerations
- Environment-based configuration management
- Webhook signature verification for Feishu events
- Input validation and sanitization
- HTTPS-only communication for production
- Secure API key storage and rotation

## Code Examples

### Database Usage (NEW)
```python
from database.connection import db
from database.models import SyncRecord, SyncConfig

# Create a new sync record
with db.get_session() as session:
    record = SyncRecord(
        source_platform='feishu',
        target_platform='notion',
        source_id='doc123',
        sync_status='pending'
    )
    session.add(record)
    session.commit()

# Query records
with db.get_session() as session:
    records = session.query(SyncRecord).filter(
        SyncRecord.sync_status == 'pending'
    ).all()
```

### HTTP Requests (NEW)
```python
import httpx

# Make HTTP request
async def fetch_data(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# Synchronous request
with httpx.Client() as client:
    response = client.post(url, json=data)
    return response.json()
```

### File Paths (NEW)
```python
import os

# Get project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Create paths
db_path = os.path.join(PROJECT_ROOT, 'feishu_notion_sync.db')
log_path = os.path.join(PROJECT_ROOT, 'logs', 'app.log')
static_path = os.path.join(PROJECT_ROOT, 'static', 'images')
```