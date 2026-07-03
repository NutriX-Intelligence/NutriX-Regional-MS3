#!/usr/bin/env python3
"""NutriX AI Diet Planner - Run Script

Usage:
    python run.py          # Start the server on default port 8000
    python run.py --port 8080  # Start on a custom port
"""

import sys
import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NutriX AI Diet Planner")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on file changes")
    args = parser.parse_args()

    border = "=" * 45
    print(f"""
{border}
   NutriX AI Diet Planner

   Running on http://{args.host}:{args.port}
   API docs at http://{args.host}:{args.port}/docs
{border}
    """)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
