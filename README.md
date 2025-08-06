# Twitter Clone Monitor with FastAPI

A production-quality Python application with FastAPI web interface that monitors fraudulent Twitter/X clones and generates weekly reports.

## Features

- **Web Interface**: Dashboard for monitoring status, mentions, and reports
- **Real-time Monitoring**: Monitors official Twitter handle and specified fraudulent clones
- **Notifications**: Sends immediate notifications via Telegram and/or email
- **Weekly Reports**: Generates PDF reports every Sunday at midnight (UTC)
- **Manual Controls**: Manually trigger monitoring, generate reports, and test notifications
- **Data Storage**: Stores state in a lightweight SQLite database
- **Error Handling**: Gracefully handles rate limits, errors, and retries

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- Twitter Developer Account with API access
- Telegram Bot Token (optional)
- Email account with SMTP access (optional)

### 2. Twitter API Setup

1. Create a Twitter Developer Account at [developer.twitter.com](https://developer.twitter.com/)
2. Create a new app and generate API keys
3. Ensure your app has the following permissions:
   - Read Tweets and user profiles
   - Read and write Direct Messages

### 3. Telegram Bot Setup (Optional)

1. Create a new bot using the [BotFather](https://t.me/BotFather) on Telegram
2. Note down the bot token
3. Get your chat ID by sending a message to [@userinfobot](https://t.me/userinfobot)

### 4. Email Setup (Optional)

1. For Gmail, enable "Less secure app access" or use an App Password
2. For other providers, check their SMTP settings

### 5. Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt