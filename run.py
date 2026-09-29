"""ChainSentry Application Runner.
Starts the FastAPI application with Uvicorn.
Supports dynamic PORT/HOST from environment variables (Render, Railway, Cloud Run, Heroku, Docker).

Usage:
    python run.py             # Production mode (binds to 0.0.0.0:$PORT or 8000)
    python run.py --reload    # Local development with auto-reloading
"""
import os
import sys
import argparse
import uvicorn
from backend.chainsentry_common.config import settings

def main():
    parser = argparse.ArgumentParser(description="Run ChainSentry Forensics Platform")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", settings.HOST),
        help="Host to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", settings.PORT)),
        help="Port to bind (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload on code change"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("WORKERS", 1)),
        help="Number of uvicorn worker processes (production)"
    )
    args = parser.parse_args()

    # Enable reload if explicitly passed or configured
    is_reload = args.reload or ("--reload" in sys.argv)

    print("=" * 60)
    print(f"[*] Starting {settings.APP_NAME} ({settings.ENVIRONMENT})")
    print(f"[*] Binding to: http://{args.host}:{args.port}")
    print(f"[*] Reload mode: {is_reload} | Workers: {args.workers}")
    print("=" * 60)

    if is_reload:
        uvicorn.run(
            "backend.api_service.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=["backend"]
        )
    else:
        uvicorn.run(
            "backend.api_service.main:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            access_log=True
        )

if __name__ == "__main__":
    main()
