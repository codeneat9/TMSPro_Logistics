#!/usr/bin/env python
"""Development server runner."""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8001,  # Use alternate port to avoid conflicts
        reload=False,
        log_level="info"
    )
