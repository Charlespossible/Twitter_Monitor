from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from typing import List, Optional
from datetime import datetime, timedelta
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

def get_app_state(request: Request):
    """Get the application state from the request"""
    return request.app.state

@router.get("/status", response_model=dict)
async def get_system_status(request: Request):
    """Get the current system status"""
    app_state = get_app_state(request)
    config = app_state.config
    storage = app_state.storage
    
    # Get all handles
    handles = [config.OFFICIAL_HANDLE] + config.CLONE_HANDLES
    
    # Get status for each handle
    handle_statuses = []
    total_mentions = 0
    
    for handle in handles:
        last_checked = storage.get_last_checked(handle)
        
        # Count mentions for this handle
        with storage._get_connection() as conn:
            import sqlite3
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM mentions WHERE handle = ?", 
                (handle,)
            )
            mention_count = cursor.fetchone()[0]
            total_mentions += mention_count
        
        handle_statuses.append({
            "handle": handle,
            "last_checked": last_checked,
            "mention_count": mention_count
        })
    
    return {
        "status": "running",
        "last_check": max((h["last_checked"] for h in handle_statuses if h["last_checked"]), default=None),
        "handles": handle_statuses,
        "total_mentions": total_mentions
    }

@router.get("/mentions", response_model=List[dict])
async def get_mentions(
    request: Request, 
    handle: Optional[str] = None, 
    limit: int = 50,
    offset: int = 0
):
    """Get mentions, optionally filtered by handle"""
    app_state = get_app_state(request)
    storage = app_state.storage
    
    with storage._get_connection() as conn:
        import sqlite3
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if handle:
            cursor.execute(
                "SELECT * FROM mentions WHERE handle = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (handle, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT * FROM mentions ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        
        return [dict(row) for row in cursor.fetchall()]

@router.post("/monitor/now")
async def trigger_monitoring(request: Request):
    """Manually trigger the monitoring process"""
    app_state = get_app_state(request)
    config = app_state.config
    storage = app_state.storage
    monitor = app_state.monitor
    notifier = app_state.notifier
    
    try:
        from main import monitor_and_notify
        monitor_and_notify(config, storage, monitor, notifier)
        return {"status": "success", "message": "Monitoring completed"}
    except Exception as e:
        logger.error(f"Error in manual monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/report/generate")
async def generate_report(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Generate a report for the specified date range"""
    app_state = get_app_state(request)
    storage = app_state.storage
    report_gen = app_state.report_gen
    
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        # Get mentions for the date range
        mentions = storage.get_weekly_mentions(start_date, end_date)
        
        if not mentions:
            return {"status": "warning", "message": "No mentions found for the specified date range"}
        
        # Generate report
        report_path = report_gen.generate_weekly_report(mentions)
        
        return {
            "status": "success", 
            "message": "Report generated successfully",
            "report_path": report_path
        }
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report/download/{filename}")
async def download_report(filename: str):
    """Download a generated report"""
    import os
    from config import Config
    
    config = Config()
    report_path = os.path.join(config.REPORT_OUTPUT_DIR, filename)
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        path=report_path,
        filename=filename,
        media_type='application/pdf'
    )

@router.get("/reports")
async def list_reports(request: Request):
    """List all available reports"""
    import os
    from config import Config
    
    config = Config()
    reports_dir = config.REPORT_OUTPUT_DIR
    
    if not os.path.exists(reports_dir):
        return {"reports": []}
    
    reports = []
    for filename in os.listdir(reports_dir):
        if filename.endswith(".pdf"):
            file_path = os.path.join(reports_dir, filename)
            stat = os.stat(file_path)
            reports.append({
                "filename": filename,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime)
            })
    
    # Sort by creation date (newest first)
    reports.sort(key=lambda r: r["created"], reverse=True)
    
    return {"reports": reports}

@router.post("/notifications/test")
async def test_notification(
    request: Request,
    notification_data: dict
):
    """Send a test notification"""
    app_state = get_app_state(request)
    notifier = app_state.notifier
    
    try:
        message = notification_data.get("message", "This is a test notification")
        use_telegram = notification_data.get("use_telegram", True)
        use_email = notification_data.get("use_email", True)
        
        results = {}
        
        if use_telegram:
            results["telegram"] = notifier.send_telegram_notification(message)
        
        if use_email:
            results["email"] = notifier.send_email_notification(
                "Test Notification", 
                f"<p>{message}</p>"
            )
        
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mentions/view", response_class=HTMLResponse)
async def view_mentions_page(request: Request):
    """Return the mentions page"""
    app_state = get_app_state(request)
    templates = app_state.templates
    return templates.TemplateResponse("mentions.html", {"request": request})

@router.get("/reports/view", response_class=HTMLResponse)
async def view_reports_page(request: Request):
    """Return the reports page"""
    app_state = get_app_state(request)
    templates = app_state.templates
    return templates.TemplateResponse("reports.html", {"request": request})