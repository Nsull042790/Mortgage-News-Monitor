# Mortgage News Monitor

A Slack-integrated mortgage news monitoring application that keeps you informed about the latest mortgage industry news, rate changes, and market developments.

## Features

- **Daily Digest**: Automated morning digest sent every weekday at 8:00 AM with the top mortgage news stories
- **Breaking News Alerts**: Continuous monitoring for urgent/breaking news with immediate Slack notifications
- **Multiple News Sources**:
  - 18+ RSS feeds from major mortgage and housing news sources
  - FHFA, HUD, Federal Reserve, CFPB, Fannie Mae, Freddie Mac
  - Mortgage News Daily, HousingWire, National Mortgage News
  - NewsAPI and GNews API integration for broader coverage
- **Smart Importance Detection**: Keyword-based analysis to identify breaking and high-priority news
- **Duplicate Prevention**: SQLite database tracks sent articles to avoid duplicates

## Quick Start

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd Mortgage-News-Monitor
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Slack Webhook URL (get from Slack App settings)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Optional: News API keys for additional coverage
NEWS_API_KEY=your-newsapi-key
GNEWS_API_KEY=your-gnews-key

# Timezone for scheduling
TIMEZONE=America/New_York

# Daily digest time (24-hour format)
DAILY_DIGEST_TIME=08:00

# How often to check for breaking news (minutes)
BREAKING_NEWS_CHECK_INTERVAL=15
```

### 3. Run the Monitor

```bash
# Start continuous monitoring
python main.py run

# Or run specific commands:
python main.py digest    # Send digest now
python main.py breaking  # Check breaking news
python main.py test      # Test without Slack
python main.py sources   # List all sources
```

## Slack Setup

### Creating a Webhook (Recommended)

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Create a new app or select existing
3. Go to "Incoming Webhooks"
4. Activate and add a new webhook to your workspace
5. Select the channel for notifications
6. Copy the webhook URL to your `.env` file

### Alternative: Bot Token

If you need more control (like posting to multiple channels):

1. Create a Slack App with `chat:write` scope
2. Install to your workspace
3. Use `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_ID` instead of webhook

## News Sources

The monitor includes RSS feeds from:

### Government & Regulatory
- FHFA (Federal Housing Finance Agency)
- HUD (Housing and Urban Development)
- Federal Reserve Press Releases
- CFPB (Consumer Financial Protection Bureau)

### GSEs & Industry
- Fannie Mae
- Freddie Mac
- Mortgage Bankers Association

### News Outlets
- Mortgage News Daily
- HousingWire
- National Mortgage News
- Inman News
- CNBC Real Estate
- MarketWatch Real Estate
- And more...

### APIs (Optional)
- NewsAPI.org
- GNews.io

## Breaking News Detection

The system analyzes news for keywords indicating important events:

**Urgent Keywords** (immediate alerts):
- Fed rate decisions, FOMC announcements
- Record high/low rates
- Market crashes or crises
- Emergency actions

**Breaking Keywords** (included in alerts):
- Mortgage rate changes
- Policy announcements
- Housing market data
- Regulatory changes

## Commands

| Command | Description |
|---------|-------------|
| `run` | Start continuous monitoring service |
| `digest` | Send daily digest immediately |
| `breaking` | Check for breaking news now |
| `sources` | List all configured news sources |
| `test` | Fetch and display news (no Slack) |

## Options

| Flag | Description |
|------|-------------|
| `--log-level` | Set logging verbosity (DEBUG, INFO, WARNING, ERROR) |

## Project Structure

```
Mortgage-News-Monitor/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Example configuration
├── src/
│   ├── config.py          # Configuration management
│   ├── database/          # SQLite database layer
│   ├── news_sources/      # RSS feeds and API clients
│   ├── importance/        # Breaking news detection
│   ├── slack/             # Slack integration
│   └── scheduler/         # Job scheduling
└── data/                  # Database storage (auto-created)
```

## Running as a Service

### Using systemd (Linux)

Create `/etc/systemd/system/mortgage-monitor.service`:

```ini
[Unit]
Description=Mortgage News Monitor
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/Mortgage-News-Monitor
ExecStart=/usr/bin/python3 main.py run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable mortgage-monitor
sudo systemctl start mortgage-monitor
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py", "run"]
```

## API Rate Limits

- **NewsAPI**: 100 requests/day (free tier)
- **GNews**: 100 requests/day (free tier)
- **RSS Feeds**: No limits

The monitor uses RSS feeds for breaking news checks to conserve API quotas, and includes APIs in daily digests for broader coverage.

## Troubleshooting

### No messages in Slack
1. Check webhook URL is correct
2. Verify the webhook channel exists
3. Run `python main.py test` to verify news fetching works

### Missing news sources
Some RSS feeds may be unavailable or change URLs. Check logs for errors and update `src/config.py` if needed.

### High API usage
Reduce `BREAKING_NEWS_CHECK_INTERVAL` or disable APIs by removing keys from `.env`.

## License

MIT License
