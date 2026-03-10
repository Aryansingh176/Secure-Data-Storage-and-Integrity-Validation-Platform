# Data Integrity Platform - MongoDB Setup Guide
BTech CSE Final Year Project

## 📋 What You Need

This guide will help you set up:
1. **MongoDB** database (local installation)
2. **Python Flask** backend server
3. **Frontend** with API integration

---

## 🔧 Step 1: Install MongoDB (Local)

### Windows Installation:

1. **Download MongoDB Community Server**
   - Go to: https://www.mongodb.com/try/download/community
   - Select version: 7.0 or latest
   - Platform: Windows
   - Package: MSI
   - Click "Download"

2. **Install MongoDB**
   - Run the downloaded `.msi` file
   - Choose "Complete" installation
   - **IMPORTANT**: Check "Install MongoDB as a Service"
   - **IMPORTANT**: Check "Install MongoDB Compass" (GUI tool)
   - Click Install

3. **Verify Installation**
   Open PowerShell and run:
   ```powershell
   mongod --version
   ```
   You should see the MongoDB version number.

4. **Start MongoDB Service**
   MongoDB should start automatically. If not:
   ```powershell
   net start MongoDB
   ```

5. **Check if MongoDB is Running**
   ```powershell
   mongosh
   ```
   If you see `test>` prompt, MongoDB is running! Type `exit` to quit.

---

## 🐍 Step 2: Install Python Dependencies

1. **Open PowerShell** in your project folder:
   ```powershell
   cd "c:\Users\hp3\Desktop\final sem project\data-integrity-platform"
   ```

2. **Create Virtual Environment** (recommended):
   ```powershell
   python -m venv venv
   ```

3. **Activate Virtual Environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   
   If you get an error about execution policy, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
   Then try activating again.

4. **Install Required Packages**:
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```

   This will install:
   - Flask (web framework)
   - flask-cors (allow frontend to access API)
   - pymongo (MongoDB driver)
   - python-dotenv (environment variables)

---

## ⚙️ Step 3: Configure Environment Variables

1. **Create `.env` file** in backend folder:
   ```powershell
   cd backend
   Copy-Item .env.example .env
   ```

2. The `.env` file contains:
   ```
   MONGO_URI=mongodb://localhost:27017/data_integrity_platform
   MONGO_DB_NAME=data_integrity_platform
   FLASK_ENV=development
   FLASK_DEBUG=True
   PORT=5000
   CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
   ```

   **No changes needed** - these default values work perfectly!

---

## 🚀 Step 4: Run the Application

You need **3 terminal windows**:

### Terminal 1: MongoDB (should already be running as service)
If not running:
```powershell
mongod
```

### Terminal 2: Flask Backend Server
Open new PowerShell terminal:
```powershell
cd "c:\Users\hp3\Desktop\final sem project\data-integrity-platform\backend"

# Activate virtual environment
..\venv\Scripts\Activate.ps1

# Run Flask server
python app.py
```

You should see:
```
✅ Connected to MongoDB: data_integrity_platform
==============================================================
🚀 Data Integrity Platform - Backend Server
==============================================================
📍 Server running on: http://localhost:5000
📊 MongoDB: data_integrity_platform
🔧 Debug mode: True
==============================================================
```

### Terminal 3: Frontend Server (Python HTTP)
Open new PowerShell terminal:
```powershell
cd "c:\Users\hp3\Desktop\final sem project\data-integrity-platform"
python -m http.server 8000
```

---

## 🌐 Step 5: Access the Application

Open your browser and go to:
- **Frontend**: http://localhost:8000/index.html
- **Backend API**: http://localhost:5000

---

## 🧪 Step 6: Test the Integration

1. **Open Frontend** (http://localhost:8000/index.html)

2. **Add Data**:
   - Enter some text (e.g., "My secret data")
   - Click "🔒 Secure Data"
   - You should see: "✓ Data secured successfully with SHA-256 hash!"

3. **View Records** (http://localhost:8000/records.html):
   - Click "View All Records" button
   - You should see your data in the table
   - Status should be "pending"

4. **Verify Integrity**:
   - Click "🔍 Verify" button on a record
   - You should see: "✓ Integrity Verified: Data is authentic and unmodified"
   - Status changes to "valid"

5. **Check MongoDB**:
   - Open MongoDB Compass (GUI tool)
   - Connect to: `mongodb://localhost:27017`
   - Database: `data_integrity_platform`
   - Collection: `data_records`
   - You should see your data stored with hash!

---

## 📊 MongoDB Compass (Visual Database Tool)

MongoDB Compass is installed with MongoDB. Use it to:
- View all records in the database
- See the hash values
- Check timestamps
- Delete records manually
- Monitor database statistics

**Connection String**: `mongodb://localhost:27017`

---

## 🛠️ Troubleshooting

### Problem: "Failed to connect to MongoDB"
**Solution**:
```powershell
# Check if MongoDB service is running
net start MongoDB

# Or start mongod manually in a new terminal
mongod
```

### Problem: "Port 5000 already in use"
**Solution**:
```powershell
# Stop the process using port 5000
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F

# Or change port in backend/.env file
PORT=5001
```

### Problem: "Port 8000 already in use"
**Solution**:
```powershell
# Use a different port for frontend
python -m http.server 8080

# Then access: http://localhost:8080/index.html
```

### Problem: Frontend shows "Could not connect to backend"
**Solutions**:
1. Make sure Flask server is running (Terminal 2)
2. Check Flask terminal for errors
3. Verify URL in js/script.js: `const API_BASE_URL = 'http://localhost:5000/api/data';`
4. Check CORS settings in backend/.env

### Problem: "pip install" fails
**Solution**:
```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Then install requirements
pip install -r requirements.txt
```

---

## 📝 API Endpoints Documentation

Your Flask backend provides these REST API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/data | Create new record with hash |
| GET | /api/data | Get all records |
| GET | /api/data/<id> | Get single record |
| POST | /api/data/<id>/verify | Verify data integrity |
| DELETE | /api/data/<id> | Delete record |
| DELETE | /api/data/clear | Delete all records |
| GET | /api/data/statistics | Get database statistics |
| GET | / | API information |
| GET | /health | Health check |

---

## 🎓 For Your VIVA Presentation

### Key Points to Explain:

1. **Architecture**:
   - Frontend: HTML/CSS/JS (served on port 8000)
   - Backend: Python Flask REST API (port 5000)
   - Database: MongoDB (port 27017)

2. **Data Flow**:
   - User enters data → Frontend sends POST to `/api/data`
   - Backend computes SHA-256 hash using Python's `hashlib`
   - Backend stores data + hash in MongoDB
   - Frontend displays records from `/api/data`

3. **Integrity Verification**:
   - User clicks Verify → Frontend calls `/api/data/<id>/verify`
   - Backend retrieves original hash from MongoDB
   - Backend recomputes hash of current data
   - Backend compares old hash vs new hash
   - If same: data is valid (not tampered)
   - If different: data was modified (invalid)

4. **Why MongoDB?**:
   - NoSQL database (flexible schema)
   - Stores JSON-like documents
   - Easy Python integration with pymongo
   - Scales well for large datasets
   - Automatic ObjectId generation

5. **Security Features**:
   - SHA-256 cryptographic hashing
   - Hash stored separately from data
   - Any data modification changes hash completely
   - Verification detects even 1-character change

---

## 🔄 Stopping the Servers

### Stop Flask Backend:
In Flask terminal: Press `Ctrl + C`

### Stop Frontend Server:
In frontend terminal: Press `Ctrl + C`

### Stop MongoDB:
```powershell
net stop MongoDB
```

---

## 📂 Project Structure

```
data-integrity-platform/
├── backend/                    # Flask Backend
│   ├── app.py                 # Main Flask server
│   ├── requirements.txt       # Python dependencies
│   ├── .env                   # Environment variables
│   ├── config/
│   │   └── database.py        # MongoDB connection
│   ├── models/
│   │   └── data_model.py      # Data schema & operations
│   └── routes/
│       └── data_routes.py     # API endpoints
├── css/
│   └── style.css              # Enterprise UI styles
├── js/
│   └── script.js              # Frontend logic (API calls)
├── index.html                 # Data entry page
├── records.html               # View records page
└── README.md                  # Project documentation
```

---

## 🎯 Next Steps

After successful setup:

1. **Test all features**: Add, View, Verify, Delete data
2. **Explore MongoDB Compass**: See your data visually
3. **Read the code**: Understand how it works
4. **Prepare for viva**: Know the architecture and data flow
5. **Add features** (optional):
   - User authentication
   - File upload with integrity checking
   - Email notifications
   - Export reports

---

## 💡 Tips for Development

- **Backend Changes**: Restart Flask server (Ctrl+C, then `python app.py`)
- **Frontend Changes**: Just refresh browser (Ctrl+R)
- **Database Changes**: View in MongoDB Compass or mongosh
- **Check Logs**: Flask terminal shows all API requests
- **Debug**: Use `print()` in Python, `console.log()` in JavaScript

---

## ✅ Success Checklist

- [ ] MongoDB installed and running
- [ ] Python dependencies installed
- [ ] .env file created in backend folder
- [ ] Flask server running on port 5000
- [ ] Frontend server running on port 8000
- [ ] Can add data from index.html
- [ ] Can view records in records.html
- [ ] Can verify integrity successfully
- [ ] Can see data in MongoDB Compass

---

**🎉 Congratulations! Your full-stack Data Integrity Platform is now running with MongoDB!**

For issues or questions, check the troubleshooting section above.
