import os
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Config
from storage import DataStorage
from twitter_monitor import TwitterMonitor
from notifications import NotificationService
from report_generator import ReportGenerator
from api.routes import router

def setup_logging(config: Config):
    """Configure logging based on environment settings"""
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('twitter_monitor.log')
        ]
    )

def monitor_and_notify(config: Config, storage: DataStorage, 
                      monitor: TwitterMonitor, notifier: NotificationService):
    """Main monitoring function that checks for mentions and sends notifications"""
    logging.info("Starting monitoring cycle")
    
    try:
        # Get all handles to monitor (official + clones)
        handles = [config.OFFICIAL_HANDLE] + config.CLONE_HANDLES
        
        # Monitor all handles
        monitor.monitor_handles(storage, handles)
        
        # Get unnotified mentions
        unnotified_mentions = storage.get_unnotified_mentions()
        
        if unnotified_mentions:
            logging.info(f"Found {len(unnotified_mentions)} new mentions to notify")
            
            # Send notifications for each mention
            for mention in unnotified_mentions:
                success = notifier.send_mention_alert(mention)
                if success:
                    logging.info(f"Sent notification for mention ID {mention['id']}")
                else:
                    logging.error(f"Failed to send notification for mention ID {mention['id']}")
            
            # Mark all as notified
            mention_ids = [m['id'] for m in unnotified_mentions]
            storage.mark_as_notified(mention_ids)
        else:
            logging.info("No new mentions found")
    
    except Exception as e:
        logging.error(f"Error in monitoring cycle: {e}")

def generate_weekly_report(config: Config, storage: DataStorage, 
                          report_gen: ReportGenerator, notifier: NotificationService):
    """Generate and send the weekly report"""
    logging.info("Starting weekly report generation")
    
    try:
        # Calculate date range for the report
        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        # Get mentions for the week
        mentions = storage.get_weekly_mentions(start_date, end_date)
        
        if mentions:
            logging.info(f"Found {len(mentions)} mentions for the weekly report")
            
            # Generate PDF report
            report_path = report_gen.generate_weekly_report(mentions)
            
            # Send report via notifications
            notifier.send_weekly_report(report_path)
            
            logging.info("Weekly report generated and sent successfully")
        else:
            logging.info("No mentions found for the weekly report")
    
    except Exception as e:
        logging.error(f"Error generating weekly report: {e}")

def create_app():
    """Create and configure the FastAPI application"""
    # Load configuration
    config = Config()
    
    # Setup logging
    setup_logging(config)
    logging.info("Starting Twitter Clone Monitor with FastAPI")
    
    # Initialize FastAPI app
    app = FastAPI(
        title="Twitter Clone Monitor",
        description="Monitor fraudulent Twitter/X clones and generate reports",
        version="1.0.0"
    )
    
    # Mount static files and templates
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
    
    # Initialize components
    storage = DataStorage(config.DATABASE_URL)
    monitor = TwitterMonitor(config)
    notifier = NotificationService(config)
    report_gen = ReportGenerator(config)
    
    # Setup scheduler
    scheduler = BackgroundScheduler()
    
    # Schedule monitoring task
    scheduler.add_job(
        func=monitor_and_notify,
        args=[config, storage, monitor, notifier],
        trigger='interval',
        minutes=config.MONITORING_INTERVAL,
        id='monitoring_job',
        name='Monitor Twitter Handles',
        replace_existing=True
    )
    
    # Schedule weekly report (Sunday at midnight UTC)
    scheduler.add_job(
        func=generate_weekly_report,
        args=[config, storage, report_gen, notifier],
        trigger=CronTrigger(day_of_week='sun', hour='0', minute='0', timezone='UTC'),
        id='weekly_report_job',
        name='Generate Weekly Report',
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    logging.info("Scheduler started")
    
    # Include API routes
    app.include_router(router, prefix="/api")
    
    # Store components in app state for access in routes
    app.state.config = config
    app.state.storage = storage
    app.state.monitor = monitor
    app.state.notifier = notifier
    app.state.report_gen = report_gen
    app.state.templates = templates
    
    # Add root route to serve dashboard
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse("dashboard.html", {"request": request})
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logging.info("Application startup")
        # Run initial monitoring
        monitor_and_notify(config, storage, monitor, notifier)
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logging.info("Shutting down...")
        scheduler.shutdown()
    
    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)