# 🚀 News Balance Backend - Deployment Guide

## 📋 Overview
Complete backend system for news processing with AI analysis using Anthropic Claude and Grok APIs.

## 🏗️ System Architecture

### Core Components:
- **Scraper** (`filter_recent_postgres.py`) - Scrapes news from Rotter.net every hour
- **Processor** (`process_articles_postgres.py`) - AI analysis with 4-stage pipeline
- **Runner** (`backend_runner_postgres.py`) - Main orchestration service
- **Monitor** (`monitor.py`) - Data consumption and monitoring

### AI Pipeline:
1. **Relevance Check** (Anthropic Claude) - Is article politically relevant?
2. **Research** (Grok API) - Internet research on the topic
3. **Technical Analysis** (Grok API) - Balanced analysis creation
4. **Journalistic Writing** (Anthropic Claude) - Final article writing

## 🗄️ Database Schema

### Tables:
- `news_items` - Main articles table
- `system_logs` - System logging
- `performance_metrics` - Performance monitoring

## 🚀 Railway Deployment

### 1. Prerequisites
- Railway account
- GitHub repository connected
- Environment variables configured

### 2. Environment Variables
Set these in Railway Dashboard:
```
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
groc_API_key=xai-...
```

### 3. Files Ready for Deployment
- ✅ `Procfile` - `web: python3 backend_runner_postgres.py`
- ✅ `requirements.txt` - All dependencies
- ✅ All Python scripts updated for PostgreSQL

### 4. Deployment Steps
1. Push code to GitHub
2. Connect repository to Railway
3. Set environment variables
4. Deploy

## 📊 Monitoring & Data Consumption

### 1. Quick Status Check
```bash
python3 quick_check.py
```
Shows basic stats and database connectivity.

### 2. Full Monitor Dashboard
```bash
python3 monitor.py
```
Interactive menu with:
- Dashboard view
- Article browsing
- System logs
- Statistics
- JSON export

### 3. Health Check
```bash
python3 health_check.py
```
Comprehensive system health check.

### 4. Dashboard Data
```bash
python3 dashboard.py
```
Generates dashboard data and saves to JSON.

## 📈 Data Storage

### All data stored in PostgreSQL:
- **Articles** - Raw and processed content
- **Logs** - System activity and errors
- **Metrics** - Performance data
- **Processing Data** - AI analysis results

### Data Access:
- Direct database queries
- Python scripts (recommended)
- JSON exports
- No additional web server needed

## 🔧 Configuration

### Timing:
- **Scraper**: Every 1 hour (3600 seconds)
- **Processor**: Every 1 hour (3600 seconds)
- **Error Retry**: 5 minutes (300 seconds)

### API Usage:
- **Anthropic**: Stages 1 & 4 (relevance + writing)
- **Grok**: Stages 2 & 3 (research + analysis)

## 📝 Logging

### Log Levels:
- **INFO** - Normal operations
- **WARNING** - Non-critical issues
- **ERROR** - Critical problems
- **DEBUG** - Detailed debugging

### Log Storage:
- Database table: `system_logs`
- File: `backend_runner.log`
- Console output

## 🚨 Troubleshooting

### Common Issues:
1. **Database Connection** - Check DATABASE_URL
2. **API Keys** - Verify ANTHROPIC_API_KEY and groc_API_key
3. **Rate Limits** - Check API usage
4. **Memory** - Monitor Railway resource usage

### Debug Commands:
```bash
# Check database
python3 -c "from monitor import NewsMonitor; m = NewsMonitor(); print(m.get_statistics())"

# Check logs
python3 -c "from monitor import NewsMonitor; m = NewsMonitor(); print(m.get_system_logs(limit=10))"

# Health check
python3 health_check.py
```

## 📊 Expected Performance

### Processing Rate:
- ~137 articles initially
- 1-5 articles processed per hour
- 4 API calls per article (2 Anthropic + 2 Grok)

### Resource Usage:
- Low CPU usage (mostly I/O)
- Moderate memory usage
- Database storage grows slowly

## 🔄 Maintenance

### Regular Tasks:
- Monitor logs for errors
- Check API usage limits
- Review processed articles quality
- Update API keys if needed

### Data Cleanup:
- Old logs can be archived
- Processed articles are permanent
- Performance metrics can be aggregated

## 📞 Support

### Files to Check:
- `monitor.py` - Main data access
- `health_check.py` - System diagnostics
- `backend_runner.log` - Runtime logs
- Railway logs - Deployment issues

### Key Metrics:
- Articles processed per day
- API response times
- Error rates
- Database size

---

**Ready for deployment! 🚀**
