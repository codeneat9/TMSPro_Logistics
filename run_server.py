#!/usr/bin/env python
"""
TMS Dashboard - Production Server Startup
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "cloud.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
