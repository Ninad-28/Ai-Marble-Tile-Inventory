#!/usr/bin/env python
import subprocess
import time
import os
import signal
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

# os.chdir('d:\\MajorProject\\Ai-Marble-Tile-Inventory\\backend')


# Kill any existing uvicorn processes
os.system('taskkill /F /IM python.exe 2>nul')
time.sleep(2)

# Start uvicorn
subprocess.run(['python', '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'])
