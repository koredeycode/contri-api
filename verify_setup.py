try:
    from app.main import app
    from app.core.config import settings
    print(f"Loaded Settings: {settings.PROJECT_NAME}")
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    exit(1)
