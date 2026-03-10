# Quick Start Commands

## Installation (One-time setup)

### 1. Install MongoDB
Download from: https://www.mongodb.com/try/download/community
Install with "Install as Service" checked

### 2. Install Python Dependencies
```powershell
cd "c:\Users\hp3\Desktop\final sem project\data-integrity-platform"
python -m venv venv
.\venv\Scripts\Activate.ps1
cd backend
pip install -r requirements.txt
```

## Daily Usage (Run these 2 commands)

### Terminal 1: Flask Backend
```powershell
cd "c:\Users\hp3\Desktop\final sem project\data-integrity-platform\backend"
..\venv\Scripts\Activate.ps1
python app.py
```

### Terminal 2: Frontend (if not already running)
```powershell
cd "c:\Users\hp3\Desktop\final sem project\data-integrity-platform"
python -m http.server 8000
```

## Access

- Frontend: http://localhost:8000/index.html
- Backend API: http://localhost:5000
- Records Page: http://localhost:8000/records.html

## MongoDB Check
```powershell
# Check if MongoDB is running
mongosh

# Or use MongoDB Compass GUI
# Connection: mongodb://localhost:27017
```

## Stop Servers
- Flask: Ctrl + C in Flask terminal
- Frontend: Ctrl + C in frontend terminal
- MongoDB: `net stop MongoDB` (or leave it running)
