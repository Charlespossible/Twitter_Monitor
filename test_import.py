# test_imports.py
try:
    from config import Config
    print("✓ Config imported successfully")
except ImportError as e:
    print(f"✗ Error importing Config: {e}")

try:
    from storage import DataStorage
    print("✓ DataStorage imported successfully")
except ImportError as e:
    print(f"✗ Error importing DataStorage: {e}")

try:
    from twitter_monitor import TwitterMonitor
    print("✓ TwitterMonitor imported successfully")
except ImportError as e:
    print(f"✗ Error importing TwitterMonitor: {e}")

try:
    from notifications import NotificationService
    print("✓ NotificationService imported successfully")
except ImportError as e:
    print(f"✗ Error importing NotificationService: {e}")

try:
    from report_generator import ReportGenerator
    print("✓ ReportGenerator imported successfully")
except ImportError as e:
    print(f"✗ Error importing ReportGenerator: {e}")

try:
    from api.routes import router
    print("✓ API routes imported successfully")
except ImportError as e:
    print(f"✗ Error importing API routes: {e}")

try:
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    print("✓ FastAPI components imported successfully")
except ImportError as e:
    print(f"✗ Error importing FastAPI components: {e}")