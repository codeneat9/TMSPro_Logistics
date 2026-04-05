#!/usr/bin/env python
"""
TMS Dashboard - Production Server
Simple startup without reload to avoid issues
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Starting TMS Dashboard Server...")
    print("=" * 60)
    print("Server will be available at: http://127.0.0.1:8000")
    print("Dashboard: http://127.0.0.1:8000/dashboard")
    print("API Docs: http://127.0.0.1:8000/docs")
    print("=" * 60)
    
    uvicorn.run(
        "cloud.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,  # Disable reload to avoid issues
        log_level="info"
    )
