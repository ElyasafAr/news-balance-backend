# Article Processor for News Balance Analyzer (Anthropic Claude)

This script reads unprocessed articles from the SQLite database and sends them to Anthropic's Claude API for analysis using a specialized prompt for Israeli media analysis.

## Features

- 🔍 **Database Integration**: Reads articles from `rotter_news.db` where `isProcessed = 0`
- 🤖 **AI Analysis**: Sends articles to Anthropic Claude 3.5 Sonnet for professional journalistic analysis
- 📊 **Progress Tracking**: Shows processing statistics and progress
- ⚡ **Rate Limiting**: Built-in delays to avoid API rate limits
- 💾 **Data Persistence**: Saves analysis results back to the database
- 🎯 **Configurable**: Easy to customize processing parameters

## Prerequisites

1. **Python 3.7+** installed
2. **Required packages** (install with `pip3 install anthropic python-dotenv`):
   - `anthropic` (Claude API client)
   - `python-dotenv`
   - `sqlite3` (built-in)

3. **Environment setup**:
   - Copy `.env - Copy.local` to `.env.local`
   - Ensure `ANTHROPIC_API_KEY` is set in `.env.local`

## Quick Start

1. **Run the script**:
   ```bash
   python3 process_articles.py
   ```

2. **Choose processing limit**:
   - Press Enter to process all unprocessed articles
   - Or enter a number to limit processing

3. **Monitor progress**:
   - The script shows real-time processing status
   - Each article is processed individually
   - Results are saved to the database

## How It Works

### 1. Database Connection
- Connects to `rotter_news.db` (SQLite)
- Looks for articles where `isProcessed = 0`
- Reads `clean_content` field for analysis

### 2. Political/Social Relevance Filter
- **Smart Pre-filtering**: Before full analysis, Claude evaluates if the article meets political/social relevance criteria
- **Decision Matrix**: Categorizes articles as HIGH, MEDIUM, or LOW relevance
- **Efficiency**: LOW relevance articles (sports, entertainment, routine business) get filtered out with explanation
- **Focus**: Only MEDIUM/HIGH relevance articles proceed to full analysis

### 3. Anthropic Claude API Processing
- Sends each relevant article with your specialized prompt
- Uses Claude 3.5 Sonnet for high-quality analysis
- Processes articles sequentially with delays

### 4. Data Storage
- Updates `isProcessed` to `1` for processed articles
- Saves analysis results in `process_data` field (JSON)
- Tracks processing metadata (timestamp, tokens used, etc.)

## Relevance Filtering

The system automatically filters articles based on political/social relevance:

### HIGH RELEVANCE (Always analyzed):
- Government policy or political decisions
- Electoral politics or political figures
- Social movements or protests
- Religious or ethnic tensions
- Legal/judicial controversies
- Military/security issues with public debate
- **Israeli-specific**: Settlement issues, judicial reform, Arab-Jewish relations, religious-secular tensions

### MEDIUM RELEVANCE (Analyzed):
- Economic policies affecting different groups
- Cultural conflicts or value disputes
- Issues that divide public opinion
- Matters affecting civil rights or freedoms

### LOW RELEVANCE (Filtered out):
- Personal stories, sports, weather
- Routine business news
- Entertainment news
- Non-controversial cultural content

## Configuration

Edit `process_config.py` to customize:
- **Database path**: Change `DATABASE_PATH` if needed
- **Anthropic settings**: Model, tokens, temperature
- **Processing delays**: Adjust `DELAY_BETWEEN_ARTICLES`
- **Analysis prompt**: Modify `DEFAULT_ANALYSIS_PROMPT`

## Available Claude Models

- **claude-3-5-sonnet-20241022**: Fast, efficient, good quality (default)
- **claude-3-opus-20240229**: Highest quality, slower processing
- **claude-3-haiku-20240307**: Fastest, basic quality

## Database Schema

The script expects a `news_items` table with these fields:
- `id`: Primary key
- `title`: Article title
- `url`: Article URL
- `clean_content`: Cleaned article content for analysis
- `isProcessed`: Boolean flag (0 = unprocessed, 1 = processed)
- `process_data`: JSON field for storing analysis results

## Output

### Console Output
- Real-time processing status
- Article details and progress
- Processing statistics
- Error messages if any

### Database Updates
- `isProcessed` field updated to `1`
- `process_data` field populated with analysis JSON
- Processing timestamp and metadata stored

### Analysis Results
Each processed article gets a JSON response containing:
- **analysis**: The full AI-generated analysis
- **model_used**: Anthropic model used (e.g., "claude-3-5-sonnet-20241022")
- **tokens_used**: Number of tokens consumed (input + output)
- **processed_at**: ISO timestamp of processing

## Error Handling

- **API Errors**: Logs and continues with next article
- **Database Errors**: Shows error messages and continues
- **Missing Content**: Skips articles without `clean_content`
- **Rate Limiting**: Built-in delays prevent API throttling

## Monitoring and Debugging

### Check Processing Status
```python
# In the script, use:
processor.show_processing_stats()
```

### View Database Contents
```sql
-- Check unprocessed articles
SELECT COUNT(*) FROM news_items WHERE isProcessed = 0;

-- Check processed articles
SELECT COUNT(*) FROM news_items WHERE isProcessed = 1;

-- View analysis results
SELECT id, title, process_data FROM news_items WHERE isProcessed = 1;
```

### Log Files
- Enable logging in `process_config.py`
- Logs saved to `article_processing.log`

## Troubleshooting

### Common Issues

1. **"ANTHROPIC_API_KEY not found"**
   - Check `.env.local` file exists
   - Verify API key is set correctly

2. **"Database not found"**
   - Ensure `rotter_news.db` exists in the same directory
   - Check file permissions

3. **"No unprocessed articles found"**
   - All articles may already be processed
   - Check database content manually

4. **API Rate Limiting**
   - Increase `DELAY_BETWEEN_ARTICLES` in config
   - Check Anthropic account usage limits

### Performance Tips

- **Batch Processing**: Process articles in smaller batches
- **Model Selection**: Use Claude 3.5 Sonnet for balanced speed/quality
- **Token Limits**: Adjust `MAX_TOKENS` based on article length
- **Parallel Processing**: Consider running multiple instances (with caution)

## Security Notes

- **API Keys**: Never commit `.env.local` to version control
- **Database**: Ensure database file has appropriate permissions
- **Rate Limiting**: Respect Anthropic's usage policies
- **Content**: Be aware that article content is sent to external API

## Support

For issues or questions:
1. Check the console output for error messages
2. Verify database structure matches expected schema
3. Ensure all dependencies are installed
4. Check Anthropic API key validity and quota

## License

This script is part of the News Balance Analyzer project.
