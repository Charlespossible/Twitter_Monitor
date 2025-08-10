import os
import logging
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Import our modules
try:
    from config import Config
    from storage import DataStorage
    from twitter_monitor import TwitterMonitor
    from notifications import NotificationService
    from report_generator import ReportGenerator
    from api.routes import router
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required modules are present in the project directory.")
    exit(1)

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
    try:
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
        
        # Add exception handlers
        @app.exception_handler(StarletteHTTPException)
        async def http_exception_handler(request: Request, exc: StarletteHTTPException):
            return HTMLResponse(
                content=f"""
                <html>
                    <head>
                        <title>Error {exc.status_code}</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; }}
                            .error {{ color: #d32f2f; }}
                            .detail {{ margin-top: 20px; }}
                        </style>
                    </head>
                    <body>
                        <h1 class="error">Error {exc.status_code}</h1>
                        <div class="detail">{exc.detail}</div>
                    </body>
                </html>
                """,
                status_code=exc.status_code
            )
        
        @app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            return HTMLResponse(
                content=f"""
                <html>
                    <head>
                        <title>Validation Error</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; }}
                            .error {{ color: #d32f2f; }}
                            .detail {{ margin-top: 20px; }}
                        </style>
                    </head>
                    <body>
                        <h1 class="error">Validation Error</h1>
                        <div class="detail">{exc}</div>
                    </body>
                </html>
                """,
                status_code=422
            )
        
        @app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logging.error(f"Unhandled exception: {exc}", exc_info=True)
            return HTMLResponse(
                content=f"""
                <html>
                    <head>
                        <title>Internal Server Error</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; }}
                            .error {{ color: #d32f2f; }}
                            .detail {{ margin-top: 20px; }}
                        </style>
                    </head>
                    <body>
                        <h1 class="error">Internal Server Error</h1>
                        <div class="detail">An unexpected error occurred. Please check the logs for details.</div>
                    </body>
                </html>
                """,
                status_code=500
            )
        
        # Mount static files and templates
        try:
            app.mount("/static", StaticFiles(directory="static"), name="static")
            templates = Jinja2Templates(directory="templates")
        except Exception as e:
            logging.error(f"Error mounting static files or templates: {e}")
            raise
        
        # Initialize components with error handling
        try:
            storage = DataStorage(config.DATABASE_URL)
        except Exception as e:
            logging.error(f"Error initializing storage: {e}")
            raise
        
        try:
            monitor = TwitterMonitor(config)
        except Exception as e:
            logging.error(f"Error initializing Twitter monitor: {e}")
            raise
        
        try:
            notifier = NotificationService(config)
        except Exception as e:
            logging.error(f"Error initializing notification service: {e}")
            raise
        
        try:
            report_gen = ReportGenerator(config)
        except Exception as e:
            logging.error(f"Error initializing report generator: {e}")
            raise
        
        # Setup scheduler
        try:
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
        except Exception as e:
            logging.error(f"Error setting up scheduler: {e}")
            raise
        
        # Include API routes
        try:
            app.include_router(router, prefix="/api")
        except Exception as e:
            logging.error(f"Error including API routes: {e}")
            raise
        
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
            try:
                return templates.TemplateResponse("dashboard.html", {"request": request})
            except Exception as e:
                logging.error(f"Error rendering dashboard: {e}")
                raise HTTPException(status_code=500, detail="Error rendering dashboard")
        
        # Add startup and shutdown events
        @app.on_event("startup")
        async def startup_event():
            logging.info("Application startup")
            # Run initial monitoring
            try:
                monitor_and_notify(config, storage, monitor, notifier)
            except Exception as e:
                logging.error(f"Error in initial monitoring: {e}")
        
        @app.on_event("shutdown")
        async def shutdown_event():
            logging.info("Shutting down...")
            try:
                scheduler.shutdown()
            except Exception as e:
                logging.error(f"Error shutting down scheduler: {e}")
        
        return app
    
    except Exception as e:
        logging.error(f"Error creating app: {e}")
        raise

app = create_app()

if __name__ == "__main__":
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        logging.error(f"Error running app: {e}")