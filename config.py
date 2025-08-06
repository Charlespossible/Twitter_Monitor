import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Twitter API credentials
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    
    # Official handle to monitor
    OFFICIAL_HANDLE = os.getenv("OFFICIAL_HANDLE", "official_handle")
    
    # List of fraudulent clone handles (comma-separated)
    CLONE_HANDLES = os.getenv("CLONE_HANDLES", "clone1,clone2").split(",")
    
    # Telegram bot settings
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # Email notification settings
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",")
    
    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///twitter_monitor.db")
    
    # Report settings
    REPORT_TIME_UTC = os.getenv("REPORT_TIME_UTC", "00:00")  # Midnight UTC
    REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "reports")
    
    # Monitoring interval (in minutes)
    MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "5"))
    
    # Logging settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")