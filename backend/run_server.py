#!/usr/bin/env python
import subprocess
import time
import os
import signal

os.chdir('d:\\MajorProject\\Ai-Marble-Tile-Inventory\\backend')

# Kill any existing uvicorn processes
os.system('taskkill /F /IM python.exe 2>nul')
time.sleep(2)

# Start uvicorn
subprocess.run(['python', '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'])
