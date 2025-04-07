#!/usr/bin/env bash

# Export keys from config.yaml options (these get injected as env vars by HA)
export OPENAI_API_KEY="$OPENAI_API_KEY"
export OPENAI_ADMIN_API_KEY="$OPENAI_ADMIN_API_KEY"

# Start the FastAPI app via uvicorn
uvicorn main:app --host 0.0.0.0 --port 5000
