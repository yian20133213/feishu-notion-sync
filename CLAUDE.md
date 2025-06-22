# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Feishu-Notion bidirectional synchronization system that enables automatic content syncing between Feishu (Lark) documents and Notion pages. The system includes image processing, format conversion, and a web management interface.

## Commands

### Running the Development Server
```bash
cd /www/wwwroot/sync.yianlu.com
python feishu_webhook_test.py
```
The Flask application runs on port 5000 with Nginx reverse proxy configured.

### Health Check
```bash
curl https://sync.yianlu.com/health
```

### Service Management
```bash
# Check if service is running
ps aux | grep python
sudo systemctl status sync-service  # if systemd service is configured
```

## Architecture

### Core Components
- **Flask Web Server**: Handles webhooks and API endpoints (`feishu_webhook_test.py`)
- **Webhook Handler**: Processes Feishu events at `/webhook/feishu`
- **Health Check**: Status endpoint at `/health`
- **Future Components** (to be implemented):
  - Notion API integration
  - Image processing with Qiniu Cloud storage
  - Database layer (MySQL) for sync records
  - Content format conversion (Markdown)

### Technology Stack
- **Backend**: Python 3.x + Flask
- **Database**: MySQL (planned)
- **Image Storage**: Qiniu Cloud CDN
- **Deployment**: Linux + Nginx + Baota Panel
- **External APIs**: Feishu API, Notion API

### Directory Structure
```
/www/wwwroot/sync.yianlu.com/
├── feishu_webhook_test.py          # Main Flask application
├── webhook/feishu/                 # Webhook endpoint directory (empty)
├── health/                         # Health check directory (empty)
├── AI开发提示词-飞书Notion同步系统.md   # Development prompts
├── 飞书-Notion双向同步系统需求文档.md    # Requirements document
└── 飞书-Notion双向同步系统设计实战.md    # Design guide
```

## Configuration

### Environment Variables (to be configured)
```bash
FEISHU_APP_ID="cli_a8d295d399a25013"
FEISHU_APP_SECRET="FTb3GlyUZlzFF6AK01k0mdtq03SpET7n"
NOTION_TOKEN="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"
QINIU_ACCESS_KEY="quisBFRU_RPX6-fO04_UrfMBukZLs1ofUDyBvgoZ"
QINIU_SECRET_KEY="IeiMby-g2i2V4qYfkot4k41B7Ztd8o8N6YHC8NAf"
QINIU_BUCKET="feishu-notion-sync"
QINIU_CDN_DOMAIN="https://cdn.yianlu.com"
```

### Service URLs
- **Main Service**: https://sync.yianlu.com
- **Webhook URL**: https://sync.yianlu.com/webhook/feishu
- **Health Check**: https://sync.yianlu.com/health
- **CDN Domain**: https://cdn.yianlu.com

## Development Notes

### Current Status
- Basic Flask webhook service is implemented and running
- SSL certificates and reverse proxy are configured
- Feishu webhook endpoint handles URL verification challenges
- Signature verification is implemented but currently disabled for testing

### Sync Strategy
- **Feishu → Notion**: Real-time automatic sync (webhook-triggered)
- **Notion → Feishu**: Manual confirmation sync (web interface)
- **Content Format**: Unified Markdown as intermediate format
- **Image Processing**: Auto-upload to Qiniu Cloud, generate CDN links

### Key Features to Implement
1. **Database Layer**: MySQL tables for sync_records, image_mappings, sync_configs
2. **Notion API Integration**: Page creation and content updates
3. **Image Processing**: Download, compress (WebP, 70% compression), upload to Qiniu
4. **Format Conversion**: Feishu rich text ↔ Markdown ↔ Notion blocks
5. **Web Management UI**: Configuration management and status monitoring

### Error Handling
- Current webhook implementation includes basic error handling
- Signature verification is available but disabled during development
- Comprehensive logging for debugging webhook events

### Security Considerations
- API credentials should be moved to environment variables
- Webhook signature verification should be enabled in production
- Web interface needs authentication mechanism