#!/bin/bash
"""
Run the FastAPI server for AskChuck.
"""

echo "Starting AskChuck API server..."
echo "API docs will be available at: http://localhost:8000/docs"
echo ""

python -m uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000
