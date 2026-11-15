#!/usr/bin/env python
"""Start the Marble AI FastAPI backend with auto-reload."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
